#include <pebble.h>
#include <stdio.h>
#include "a/a/aa.h"
#include "b/b.h"
#include "b/a/a/baa.h"
#include "a/b/ab.h"
#include "side_effect.h"

static void __attribute__ ((noinline)) dynamic_stack2(int i) {
  uint16_t dyn_stack[i];
  use_ptr((uint32_t)&dyn_stack);
//  use_ptr(i);
}

char foo[200] = "foo";

static double some_double_value;

static void __attribute__ ((noinline)) uses_doubles2(uint8_t i) {
  double double_value = i * some_double_value;
  double_value /= 4.8;
  uint32_t int_value = (uint32_t)double_value;
  use_ptr(int_value);
}

static void init_values(void) {
  some_double_value = 2.4;
}

static void call_funcs() {
  func_aa();
  func_ab();
  func_b();
  func_baa();
}

int main(void) {
  APP_LOG(APP_LOG_LEVEL_DEBUG, "%s", foo);
  init_values();
  dynamic_stack2(1);
  dynamic_stack2(2);
  uses_doubles2(2);

  call_funcs();

  window_destroy(window_create());

  return 0;
}
