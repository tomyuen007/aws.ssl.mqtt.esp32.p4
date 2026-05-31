add_library(usermod_camera INTERFACE)

target_sources(usermod_camera INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/modcamera.c
)

target_include_directories(usermod_camera INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    # EXTRA_COMPONENT_DIRS=/opt/esp32-camera (set in Dockerfile + docker-compose)
    $ENV{EXTRA_COMPONENT_DIRS}/driver/include
    $ENV{EXTRA_COMPONENT_DIRS}/driver/private_include
    $ENV{EXTRA_COMPONENT_DIRS}/conversions/include
)

target_link_libraries(usermod INTERFACE usermod_camera)
