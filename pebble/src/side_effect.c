#include "side_effect.h"

uint32_t used;
void use_ptr(uint32_t value) {
  used = value;
}

