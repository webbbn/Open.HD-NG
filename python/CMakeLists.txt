
# Find the wifibroadcast paths
find_path(WFB_INCLUDE_DIR wifibroadcast/fec.hh)

# Find the python library.
find_package(PythonLibs REQUIRED)
include_directories(
  ${PYTHON_INCLUDE_PATH}
  ${PROJECT_SOURCE_DIR}/python
  ${WFB_INCLUDE_DIR}/wifibroadcast)

# Compile with cython
include(UseCython)

# Build the FEC cython interface
cython_add_module(fec)
link_directories(${PROJECT_BINARY_DIR})
target_link_libraries(fec ${PYTHON_LIBRARY} ${Extra_Libraries} wifibroadcast)

# Build the py_v4l2 cython interface
cython_add_module(py_v4l2)
target_link_libraries(py_v4l2  ${PYTHON_LIBRARY} ${Extra_Libraries} v4l2)

# Install the cython targets.
install(TARGETS fec py_v4l2 DESTINATION ${RELATIVE_PYTHON_DIR})

# Install the python executable scripts
install(PROGRAMS openhd_controller DESTINATION ${BinDir})

# Install the python libraries
install(FILES
  format_as_table.py
  camera.py
  telemetry.py
  MultiWii.py
  MavlinkTelemetry.py
  transmitter.py
  settings.py
  wifi_settings.py
  openhd_settings.py
  wfb_bridge_settings.py
  DESTINATION ${RELATIVE_PYTHON_DIR})
