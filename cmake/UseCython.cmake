# This allows to link Cython files
# Examples:
# 1) to compile assembly.pyx to assembly.so:
#   cython_add_module(assembly)
# 2) to compile assembly.pyx and something.cpp to assembly.so:
#   cython_add_module(assembly something.cpp)

find_program(CYTHON NAMES cython3 cython cython.py)

if(NOT CYTHON_INCLUDE_DIRECTORIES)
  set(CYTHON_INCLUDE_DIRECTORIES .)
endif(NOT CYTHON_INCLUDE_DIRECTORIES)

macro(cython_add_module name)
  add_custom_command(
    OUTPUT ${name}.cpp
    COMMAND ${CYTHON}
    ARGS --cplus -3 -I ${CYTHON_INCLUDE_DIRECTORIES} -o ${name}.cpp ${CMAKE_CURRENT_SOURCE_DIR}/${name}.pyx
    DEPENDS ${name}.pyx
    COMMENT "Cython source")
  add_library(${name} MODULE ${name}.cpp ${ARGN})
  set_target_properties(${name} PROPERTIES PREFIX "")
  if (CMAKE_HOST_WIN32)
    set_target_properties(${name} PROPERTIES SUFFIX ".pyd")
  endif(CMAKE_HOST_WIN32)
endmacro(cython_add_module)
