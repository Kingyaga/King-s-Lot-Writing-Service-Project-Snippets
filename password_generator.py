import secrets
import string
from typing import List, Dict

class AdvancedPasswordGenerator:
    """
    A class for generating secure passwords that meet advanced requirements.
    
    This generator uses cryptographically strong random number generation
    and ensures a mix of character types for enhanced security.
    """

    def __init__(self):
        self.char_sets: Dict[str, str] = {
            'lowercase': string.ascii_lowercase,
            'uppercase': string.ascii_uppercase,
            'digits': string.digits,
            'symbols': "!@#$%^&*()_+-=[]{}|;:,.<>?"
        }
        
    def generate_password(self, length: int = 20) -> str:
        """
        Generate a secure password of the specified length.
        
        Args:
            length (int): The desired length of the password. Default is 20.
        
        Returns:
            str: A secure password meeting the specified requirements.
        
        Time Complexity: O(n), where n is the length of the password.
        Space Complexity: O(n) for the resulting password string.
        """
        if length < 8:
            raise ValueError("Password length must be at least 8 characters.")
        
        # Ensure at least one character from each set
        password: List[str] = [secrets.choice(chars) for chars in self.char_sets.values()]
        
        # Fill the rest of the password
        for _ in range(length - len(self.char_sets)):
            password.append(secrets.choice(self.get_all_chars()))
        
        # Shuffle the password to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    def get_all_chars(self) -> str:
        """
        Get all possible characters for password generation.
        
        Returns:
            str: A string containing all possible characters.
        
        Time Complexity: O(1) - constant time operation.
        Space Complexity: O(1) - constant space used.
        """
        return ''.join(self.char_sets.values())

# Usage example
if __name__ == "__main__":
    generator = AdvancedPasswordGenerator()
    password = generator.generate_password()
    print(f"Generated password: {password}")