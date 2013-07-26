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

import struct

from twisted.trial.unittest import TestCase

from tryfer import formatters

class TestFormatters(TestCase):
    def test_ipv4_to_int(self):
        """ Thrift expects ipv4 address to be a signed 32-bit integer.
        Previously this function converted ip addresses to an unsigned 32-bit
        int. struct.pack is strict about integer overflows for signed 32-bit
        integers, so this function very much needs to produce a signed integer
        to allow IP addresses in the upper half to work
        """
        # ip that doesn't overflow in signed 32-bit
        low_ip = '127.0.0.1'
        # ip that does overflow in signed 32-bit
        high_ip = '172.17.1.1'

        low_ip_as_int = formatters.ipv4_to_int(low_ip)
        high_ip_as_int = formatters.ipv4_to_int(high_ip)

        # both parsed ips should be packable as signed 32-bit int
        struct.pack('!i', low_ip_as_int)
        struct.pack('!i', high_ip_as_int)
