#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "superlu::superlu" for configuration "Release"
set_property(TARGET superlu::superlu APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(superlu::superlu PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libsuperlu.a"
  )

list(APPEND _cmake_import_check_targets superlu::superlu )
list(APPEND _cmake_import_check_files_for_superlu::superlu "${_IMPORT_PREFIX}/lib/libsuperlu.a" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
