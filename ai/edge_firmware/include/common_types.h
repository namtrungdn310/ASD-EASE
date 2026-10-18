#pragma once

enum class Availability
{
    NOT_IMPLEMENTED,
    UNAVAILABLE,
    READY,
    ERROR
};

enum class EngineeringState
{
    NORMAL,
    ATTENTION,
    UNCERTAIN,
    CALIBRATING
};
