cmake_minimum_required(VERSION 3.16)

# Must come before project() — resolves IDF_PATH and toolchain
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

project(esp32p4_mqtt)
