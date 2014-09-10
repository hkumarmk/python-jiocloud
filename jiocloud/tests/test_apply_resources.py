#    Copyright Reliance Jio Infocomm, Ltd.
#    Author: Soren Hansen <Soren.Hansen@ril.com>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
import mock
import os
import StringIO
import unittest
from contextlib import nested
from jiocloud.apply_resources import ApplyResources

class TestApplyResources(unittest.TestCase):
    server_data = [('foo1_abc123', '93138146-2275-4e18-b41e-3957aa13e73a'),
                   ('foo2_abc124', '26af0276-83e1-4b68-870e-ff3250be8e8f'),
                   ('foo4_bc124', '677388b7-b5ac-418b-b671-6b930dc8003a'),
                   ('bar2', '381877b2-12c5-4831-95ed-1d7518bb7e8c'),
                   ('baz', '59e5dd8d-2063-4943-98de-df206e462849')]

    def setUp(self):
        super(TestApplyResources, self).setUp()
        os.environ['OS_USERNAME'] = 'os_username'
        os.environ['OS_PASSWORD'] = 'os_pasword'
        os.environ['OS_AUTH_URL'] = 'http://example.com/'
        os.environ['OS_TENANT_NAME'] = 'tenant_name'
        os.environ['OS_REGION_NAME'] = 'region_name'

    def fake_server_data(self, nova_client):
        def fake_server(name, uuid):
            s = mock.Mock()
            s.configure_mock(name=name, id=uuid)
            return s
        server_list = [fake_server(*s) for s in self.server_data]
        nova_client.servers.list.return_value = server_list

    def test_get_existing_servers(self):
        apply_resources = ApplyResources()
        with mock.patch.object(apply_resources, 'get_nova_client') as get_nova_client:
            nova_client = get_nova_client.return_value
            self.fake_server_data(nova_client)
            self.assertEquals(apply_resources.get_existing_servers(), [s[0] for s in self.server_data])
            self.assertEquals(apply_resources.get_existing_servers(project_tag='abc123'),
                              ['foo1_abc123'])
            self.assertEquals(apply_resources.get_existing_servers(project_tag='abc124'),
                              ['foo2_abc124'])
            self.assertEquals(apply_resources.get_existing_servers(project_tag='bc124'),
                              ['foo4_bc124'])
            self.assertEquals(apply_resources.get_existing_servers(project_tag='bc124', attr_name='id'),
                              ['677388b7-b5ac-418b-b671-6b930dc8003a'])

    def test_generate_desired_servers(self):
        apply_resources = ApplyResources()
        self.assertEquals(apply_resources.generate_desired_servers({'foo': {'number': 5 }}, project_tag='foo'),
                          [{'name': 'foo1_foo', 'number': 5},
                           {'name': 'foo2_foo', 'number': 5},
                           {'name': 'foo3_foo', 'number': 5},
                           {'name': 'foo4_foo', 'number': 5},
                           {'name': 'foo5_foo', 'number': 5}
                          ])
        self.assertEquals(apply_resources.generate_desired_servers({'foo': {'number': 5 },
                                                                    'bar': {'number': 2 }}, project_tag='foo'),
                          [{'name': 'foo1_foo', 'number': 5},
                           {'name': 'foo2_foo', 'number': 5},
                           {'name': 'foo3_foo', 'number': 5},
                           {'name': 'foo4_foo', 'number': 5},
                           {'name': 'foo5_foo', 'number': 5},
                           {'name': 'bar1_foo', 'number': 2},
                           {'name': 'bar2_foo', 'number': 2},
                          ])
        self.assertEquals(apply_resources.generate_desired_servers({'foo': {'number': 0 },
                                                                    'bar': {'number': 2 }}),
                          [{'name': 'bar1', 'number': 2},
                           {'name': 'bar2', 'number': 2}])

    def test_servers_to_create(self):
        apply_resources = ApplyResources()
        with mock.patch.multiple(apply_resources,
                                 get_nova_client=mock.DEFAULT,
                                 read_resources=mock.DEFAULT) as mocks:
            get_nova_client = mocks['get_nova_client']
            read_resources = mocks['read_resources']
            read_resources.return_value = {'foo': {'number': 1},
                                           'bar': {'number': 2}}

            nova_client = get_nova_client.return_value
            self.fake_server_data(nova_client)

            self.assertEquals(apply_resources.servers_to_create('fake_path'),
                              [{'name': 'foo1', 'number': 1},
                               {'name': 'bar1', 'number': 2}])

    def test_create_servers(self):
        apply_resources = ApplyResources()
        with nested(
               mock.patch('__builtin__.file'),
               mock.patch('time.sleep'),
               mock.patch.object(apply_resources, 'create_server'),
               mock.patch.object(apply_resources, 'get_nova_client')
            ) as (file_mock, sleep, create_server, get_nova_client):
            ids = [10,11]
            status = {10: ['ACTIVE', 'BUILD', 'BUILD'], 11: ['ACTIVE', 'BUILD']}

            def fake_create_server(*args, **kwargs):
                return ids.pop()

            create_server.side_effect = fake_create_server

            def server_get(id):
                mm = mock.MagicMock()
                mm.status = status[id].pop()
                return mm

            get_nova_client.return_value.servers.get.side_effect = server_get

            file_mock.side_effect = lambda f: StringIO.StringIO('test user data')

            apply_resources.create_servers([{'name': 'foo1', 'networks':  ['someid']},
                                            {'name': 'foo2', 'networks':  ['someid']}], 'somefile', 'somekey')

            create_server.assert_any_call(mock.ANY, 'somekey', name='foo1', networks=['someid'])
            create_server.assert_any_call(mock.ANY, 'somekey', name='foo2', networks=['someid'])

            for call in create_server.call_args_list:
                self.assertEquals(call[0][0].read(), 'test user data')

            for s in status.values():
                self.assertEquals(s, [], 'create_servers stopped polling before server left BUILD state')

