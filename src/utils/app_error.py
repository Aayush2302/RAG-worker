# utils/app_error.py

class AppError(Exception):
    """
    Custom application error matching TypeScript AppError
    """
    
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.is_operational = True
    
    def __str__(self):
        return f"AppError({self.status_code}): {self.message}"
