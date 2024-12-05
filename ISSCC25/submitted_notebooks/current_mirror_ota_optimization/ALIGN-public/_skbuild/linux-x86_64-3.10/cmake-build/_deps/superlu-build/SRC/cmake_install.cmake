# Install script for directory: /home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-src/SRC

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-install")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set path to fallback-tool for dependency-resolution.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE STATIC_LIBRARY FILES "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-build/SRC/libsuperlu.a")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include" TYPE FILE FILES
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-src/SRC/supermatrix.h"
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-src/SRC/slu_Cnames.h"
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-src/SRC/slu_dcomplex.h"
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-src/SRC/slu_scomplex.h"
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-src/SRC/slu_util.h"
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-src/SRC/superlu_enum_consts.h"
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-build/SRC/superlu_config.h"
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-src/SRC/slu_sdefs.h"
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-src/SRC/slu_ddefs.h"
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-src/SRC/slu_cdefs.h"
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-src/SRC/slu_zdefs.h"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/superlu/superluTargets.cmake")
    file(DIFFERENT _cmake_export_file_changed FILES
         "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/superlu/superluTargets.cmake"
         "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-build/SRC/CMakeFiles/Export/29844f99febfd7af969da705a88a5078/superluTargets.cmake")
    if(_cmake_export_file_changed)
      file(GLOB _cmake_old_config_files "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/superlu/superluTargets-*.cmake")
      if(_cmake_old_config_files)
        string(REPLACE ";" ", " _cmake_old_config_files_text "${_cmake_old_config_files}")
        message(STATUS "Old export file \"$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/cmake/superlu/superluTargets.cmake\" will be replaced.  Removing files [${_cmake_old_config_files_text}].")
        unset(_cmake_old_config_files_text)
        file(REMOVE ${_cmake_old_config_files})
      endif()
      unset(_cmake_old_config_files)
    endif()
    unset(_cmake_export_file_changed)
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/superlu" TYPE FILE FILES "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-build/SRC/CMakeFiles/Export/29844f99febfd7af969da705a88a5078/superluTargets.cmake")
  if(CMAKE_INSTALL_CONFIG_NAME MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
    file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/superlu" TYPE FILE FILES "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-build/SRC/CMakeFiles/Export/29844f99febfd7af969da705a88a5078/superluTargets-release.cmake")
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/cmake/superlu" TYPE FILE FILES
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-build/SRC/superluConfig.cmake"
    "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-build/SRC/superluConfigVersion.cmake"
    )
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-build/SRC/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
