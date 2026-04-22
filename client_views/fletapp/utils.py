from typing import Generic, TypeVar, Callable

T = TypeVar('T')
class Grid(Generic[T]):
    def __init__(self, rows, cols, initial_factory: Callable[[], T]):
        self.rows = rows
        self.cols = cols
        self._grid: list[list[T]] = [
            [initial_factory() for _ in range(cols)]
            for _ in range(rows)
        ]

    def get(self, row, col):
        """Retrieve an element and check bounds."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self._grid[row][col]
        raise IndexError("Matrix coordinates out of range")

    def set(self, row, col, value) -> T:
        """Set an element and check bounds. It outputs the element that was set."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self._grid[row][col] = value
            return value
        else:
            raise IndexError("Grid index out of range")

    def __str__(self):
        return "\n".join([" ".join([str(item) for item in row]) for row in self._grid])
