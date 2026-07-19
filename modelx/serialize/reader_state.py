"""Restore the system's models when a model read fails.

``ModelReader.read_model`` for serializer versions 4-7 builds the new
model in the live system: ``parse_dir`` creates a model (making it
current), and ``RenameParser`` renames it to its saved name immediately
during parsing, displacing a same-named existing model to
``<name>_BAK<n>``.  When the read fails halfway, closing the half-built
model does not undo those side effects on its own: the displaced model
would stay under its backup name, and no model would be current even
though the previously current model still exists.

``SystemStateSnapshot`` records the state before the read so that the
except path can put it back after closing the half-built model.  On a
successful read the displaced model intentionally keeps its backup name,
so the snapshot is simply discarded.
"""


class SystemStateSnapshot:

    def __init__(self, system):
        self.system = system
        self.models = dict(system.models)
        self.currentmodel = system.currentmodel

    def restore(self):
        """Called after a failed read, once the half-built model is closed."""
        system = self.system

        for name, model in self.models.items():
            if (model.name != name
                    and system.models.get(model.name) is model
                    and name not in system.models):
                system.rename_model(new_name=name, old_name=model.name)

        current = self.currentmodel
        if (system.currentmodel is None
                and current is not None
                and system.models.get(current.name) is current):
            system.currentmodel = current
