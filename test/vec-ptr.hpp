// Copyright 2016 The RamFuzz contributors. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <vector>
namespace ns1 {

class A {
public:
  int f() const { return 10; }
};

class B {
public:
  int sum = 5;
  void f1(const std::vector<A *> &v) {
    if (!v.empty())
      sum = v[0]->f() / 2;
  }
  void f2(const std::vector<int *> &v) {
    if (!v.empty())
      sum += *v[0];
    if (!v.empty())
      sum -= *v[0];
  }
  void f3(const std::vector<void *> &v) {}
};

} // namespace ns1