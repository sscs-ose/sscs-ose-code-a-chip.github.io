# Install script for directory: /home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public

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

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/json-build/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/spdlog-build/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/superlu-build/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/ilpsolverif-build/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/PlaceRouteHierFlow/cmake_install.cmake")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-install/align/PnR.cpython-310-x86_64-linux-gnu.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-install/align/PnR.cpython-310-x86_64-linux-gnu.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-install/align/PnR.cpython-310-x86_64-linux-gnu.so"
         RPATH "$ORIGIN/thirdparty:/usr/lib/lp_solve")
  endif()
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-install/align/PnR.cpython-310-x86_64-linux-gnu.so")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-install/align" TYPE SHARED_LIBRARY FILES "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/PlaceRouteHierFlow/PnR.cpython-310-x86_64-linux-gnu.so")
  if(EXISTS "$ENV{DESTDIR}/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-install/align/PnR.cpython-310-x86_64-linux-gnu.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-install/align/PnR.cpython-310-x86_64-linux-gnu.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-install/align/PnR.cpython-310-x86_64-linux-gnu.so"
         OLD_RPATH "/usr/lib/lp_solve:/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/_deps/cbc-build/lib:"
         NEW_RPATH "$ORIGIN/thirdparty:/usr/lib/lp_solve")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-install/align/PnR.cpython-310-x86_64-linux-gnu.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/PlaceRouteHierFlow/CMakeFiles/PnR.dir/install-cxx-module-bmi-Release.cmake" OPTIONAL)
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
if(CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/install_local_manifest.txt"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
if(CMAKE_INSTALL_COMPONENT)
  if(CMAKE_INSTALL_COMPONENT MATCHES "^[a-zA-Z0-9_.+-]+$")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INSTALL_COMPONENT}.txt")
  else()
    string(MD5 CMAKE_INST_COMP_HASH "${CMAKE_INSTALL_COMPONENT}")
    set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INST_COMP_HASH}.txt")
    unset(CMAKE_INST_COMP_HASH)
  endif()
else()
  set(CMAKE_INSTALL_MANIFEST "install_manifest.txt")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  file(WRITE "/home/adair/Documents/CAD/sscs-ose-code-a-chip.github.io/ISSCC25/submitted_notebooks/current_mirror_ota_optimization/ALIGN-public/_skbuild/linux-x86_64-3.10/cmake-build/${CMAKE_INSTALL_MANIFEST}"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
endif()
