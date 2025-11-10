import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function Users() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">User Management</h1>
        <p className="text-gray-500">Manage dashboard users and permissions</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Users</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            User management will be fully implemented in SHARD-20.
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Current user: Check the sidebar for your username and role.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}



