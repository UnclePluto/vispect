class SessionRouter:
    def db_for_read(self, model, **hints):
        return 'control' if model._meta.app_label == 'sessions' else None
    def db_for_write(self, model, **hints):
        return self.db_for_read(model, **hints)
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'migration'
