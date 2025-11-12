from os import path, walk

def enumerate_dir_recursive(dir_path: str) -> list[str]:
	paths = []

	for root, subdirs, files in walk(dir_path):
		paths.extend([path.join(root, file) for file in files])

		for subdir in subdirs:
			paths.extend(enumerate_dir_recursive(path.join(root, subdir)))

	return paths