"""A module to handle LINE token rotation.

This module provides a class to handle LINE token rotation.
"""


class LineTokenRotator:
    """A class to handle LINE token rotation.
    
    Attributes:
        tokens (list[str]): The LINE Notify tokens.
        index (int): The index of the current token.
    """

    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.index = 0

    def current_token(self) -> str:
        """Get the current LINE Notify token.
        
        Returns:
            str: The current LINE Notify token.
        """

        return self.tokens[self.index]

    def rotate_token(self) -> None:
        """Rotate the LINE Notify token."""

        self.index = (self.index + 1) % len(self.tokens)
