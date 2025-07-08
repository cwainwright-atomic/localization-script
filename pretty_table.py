from typing import Any


class PrettyTable:
    def __init__(
        self, data: list[list[str | Any]], headers: list[str] | None = None
    ) -> None:
        self.data = data
        if headers:
            self.data.insert(0, headers)
            self.headers = True

    def __str__(self) -> str:
        if not self.data:
            return "No data provided."

        # Transpose to get columns
        cols: list[tuple[str, ...]] = list(zip(*self.data))
        col_widths: list[int] = [max(len(str(item)) for item in col) for col in cols]

        result = ""

        if self.headers:
            headers = self.data.pop(0)  # Remove headers from data for pretty printing

            pretty_row = " | ".join(
                str(item).ljust(width) for item, width in zip(headers, col_widths)
            )
            result += pretty_row + "\n"

            result += "-" * len(pretty_row) + "\n"

        for row in self.data:
            pretty_row = " | ".join(
                str(item).ljust(width) for item, width in zip(row, col_widths)
            )
            result += pretty_row + "\n"

        return result


# Example usage:
if __name__ == "__main__":
    headers = ["Name", "Age", "City"]
    data = [
        ["Alice", 23255, "New York"],
        ["Bob", 34, "San Francisco"],
        ["Charlie", 28, "Los Angeles"],
    ]
    print(PrettyTable(data, headers=headers))
