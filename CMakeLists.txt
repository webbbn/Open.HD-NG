
cmake_minimum_required(VERSION 3.5)
project(Open.HD-NG)

# Point to our local cmake files
set(CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")

# Default the CMAKE_INSTALL_PREFIX
IF(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
  SET(CMAKE_INSTALL_PREFIX "/" CACHE PATH "Change the default installation director (default=/)" FORCE)
ENDIF(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)

# Generate version information
ADD_CUSTOM_COMMAND(
  OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/version.cc ${CMAKE_CURRENT_BINARY_DIR}/_version.cc
  COMMAND ${CMAKE_COMMAND} -P ${PROJECT_SOURCE_DIR}/cmake/version.cmake
  )

# Build optimized
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -O3 -DNDEBUG")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -DNDEBUG")

# Add the usr directory to most of the paths if the installcation directory is /
set(BinDir "usr/bin")
set(LibDir "usr/lib")
set(IncludeDir "usr/include")
set(PythonDistDir "dist-packages")

# We have submodule, so we need git to update the submodule
find_package(Git QUIET)

# Update submodules as needed
if(GIT_FOUND AND EXISTS "${PROJECT_SOURCE_DIR}/.git")
  option(GIT_SUBMODULE "Check submodules during build" OFF)
  if(GIT_SUBMODULE)
    message(STATUS "Submodule update")
    execute_process(COMMAND ${GIT_EXECUTABLE} submodule update --init --recursive
      WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
      RESULT_VARIABLE GIT_SUBMOD_RESULT)
    if(NOT GIT_SUBMOD_RESULT EQUAL "0")
      message(FATAL_ERROR "git submodule update --init failed with ${GIT_SUBMOD_RESULT}, please checkout submodules")
    endif()
  endif()
endif()

# Ensure the mavlink directory was checked out successfully
if(NOT EXISTS "${PROJECT_SOURCE_DIR}/modules/mavlink/protocol.h")
  message(FATAL_ERROR "The mavlink submodule was not downloaded! Please update submodules and try again.")
endif()

# Add the local include directory to the include path
include_directories(${PROJECT_SOURCE_DIR}/include)

# Find the python3 interpreter
if (${CMAKE_VERSION} VERSION_LESS "3.12.0")
  set(Python_ADDITIONAL_VERSIONS "3")
  set(PYTHON_EXECUTABLE "/usr/bin/python3")
  find_package(PythonInterp 3.0 REQUIRED)
  set(RELATIVE_PYTHON_DIR "${LibDir}/python${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}/${PythonDistDir}/openhd")
else ()
  find_package(Python3 COMPONENTS Interpreter)
  set(RELATIVE_PYTHON_DIR "${LibDir}/python${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}/${PythonDistDir}/openhd")
endif ()

# Add the python directory to the list of directories to build
add_subdirectory(python)

# Find the boost libraries
find_package(Boost REQUIRED COMPONENTS
  program_options
  system
  filesystem
  log)
include_directories(${Boost_INCLUDE_DIR})

# Add the mavlink directory to the build
include_directories(${PROJECT_SOURCE_DIR}/modules/mavlink/common)

# Install the configuration files
install(FILES "${PROJECT_SOURCE_DIR}/conf/openhd" DESTINATION etc/default COMPONENT configuratios)

# Install the service files
install(FILES "${PROJECT_SOURCE_DIR}/services/openhd.service" DESTINATION etc/systemd/system COMPONENT configuratios)

# Add the debian debian package dependencies
set(CPACK_DEBIAN_PACKAGE_DEPENDS "libboost-all-dev cython3 libv4l-dev")

# Add rules to build a debian package
set(CPACK_GENERATOR "DEB")
set(CPACK_DEBIAN_PACKAGE_MAINTAINER "webbbn@gmail.con")
set(CPACK_DEBIAN_FILE_NAME "DEB-DEFAULT")
set(CPACK_PACKAGE_VERSION "0.1.0")
set(CPACK_PACKAGE_INSTALL_DIRECTORY /)
set(CPACK_SET_DESTDIR true)
set(CPACK_INSTALL_PREFIX /)
include(CPack)
