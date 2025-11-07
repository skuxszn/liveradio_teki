/**
 * Connection tester component.
 * Tests connection to external services like AzuraCast.
 */

import { useState } from 'react';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { configService } from '@/services/config.service';

export function ConnectionTester() {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    message: string;
    details?: any;
  } | null>(null);

  const testConnection = async () => {
    setTesting(true);
    setResult(null);

    try {
      const response = await configService.testAzuraCastConnection();
      setResult({
        success: response.success,
        message: response.message,
        details: {
          version: response.azuracast_version,
          online: response.online,
          tested_at: response.tested_at,
        },
      });
    } catch (error: any) {
      setResult({
        success: false,
        message: error.response?.data?.detail || 'Failed to test connection',
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <Button
          type="button"
          variant="outline"
          onClick={testConnection}
          disabled={testing}
        >
          {testing ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Testing...
            </>
          ) : (
            <>Test AzuraCast Connection</>
          )}
        </Button>
      </div>

      {result && (
        <Alert variant={result.success ? 'default' : 'destructive'}>
          <div className="flex items-start gap-2">
            {result.success ? (
              <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 text-red-500 mt-0.5" />
            )}
            <div className="flex-1">
              <AlertDescription>
                <p className="font-medium">{result.message}</p>
                {result.details && result.success && (
                  <div className="mt-2 text-sm space-y-1">
                    <p>Version: {result.details.version || 'Unknown'}</p>
                    <p>Status: {result.details.online ? 'Online' : 'Offline'}</p>
                    <p className="text-xs text-gray-500">
                      Tested at: {new Date(result.details.tested_at).toLocaleString()}
                    </p>
                  </div>
                )}
              </AlertDescription>
            </div>
          </div>
        </Alert>
      )}
    </div>
  );
}


