# Copyright 2012 Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from twisted.trial.unittest import TestCase

from tryfer.tracers import get_tracers, set_tracers, push_tracer


class GlobalTracerTests(TestCase):
    def tearDown(self):
        set_tracers([])

    def test_set_tracers(self):
        dummy_tracer = object()

        set_tracers([dummy_tracer])
        self.assertEqual(get_tracers(), [dummy_tracer])

    def test_push_tracer(self):
        dummy_tracer = object()
        dummy_tracer2 = object()

        push_tracer(dummy_tracer)
        self.assertEqual(get_tracers(), [dummy_tracer])

        push_tracer(dummy_tracer2)

        self.assertEqual(get_tracers(), [dummy_tracer, dummy_tracer2])
