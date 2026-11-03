from pathlib import Path

source_file = Path("openEMS_frequency_values.txt")

# Read values
values = [
    float(line.strip())
    for line in source_file.read_text().splitlines()
    if line.strip()
]

# Calculate differences between neighbouring values
differences = [
    values[i + 1] - values[i]
    for i in range(len(values) - 1)
]

# Output file in the same directory
output_file = source_file.parent / f"{source_file.stem}_differences.txt"

# Write differences
output_file.write_text(
    "\n".join(f"{difference:.6e}" for difference in differences) + "\n"
)

print(f"Saved differences to: {output_file}")