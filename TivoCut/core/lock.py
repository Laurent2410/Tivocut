import os
import sys

class SingleInstanceLock:
    def __init__(self, lock_path: str):
        self.lock_path = lock_path
        self.fp = None

    def acquire(self) -> bool:
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
        self.fp = open(self.lock_path, "a+")

        if sys.platform.startswith("win"):
            import msvcrt
            try:
                # lock 1 byte (exclusif, non-bloquant)
                msvcrt.locking(self.fp.fileno(), msvcrt.LK_NBLCK, 1)
                self.fp.seek(0)
                self.fp.truncate()
                self.fp.write("locked\n")
                self.fp.flush()
                return True
            except OSError:
                # déjà locké par une autre instance
                try:
                    self.fp.close()
                except Exception:
                    pass
                self.fp = None
                return False
        else:
            # hors Windows: pas supporté ici
            return True

    def release(self) -> None:
        if not self.fp:
            # si jamais l'app a planté avant
            self._try_remove_lockfile()
            return

        try:
            if sys.platform.startswith("win"):
                import msvcrt
                self.fp.seek(0)
                msvcrt.locking(self.fp.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            try:
                self.fp.close()
            except Exception:
                pass
            self.fp = None
            self._try_remove_lockfile()

    def _try_remove_lockfile(self) -> None:
        # On supprime le fichier lock si possible
        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        except Exception:
            # si Windows refuse (antivirus, droits…), ce n'est pas bloquant
            pass