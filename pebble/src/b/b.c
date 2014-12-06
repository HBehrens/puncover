#include "b.h"
#include "side_effect.h"
int func_b() {
  use_ptr(1);
  return 1;
}