/**
 * Token generator component.
 * Generates new security tokens.
 */

import { useState } from 'react';
import { RefreshCw, Copy, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { configService } from '@/services/config.service';
import { ConfirmDialog } from '@/components/feedback/ConfirmDialog';
import { toast } from '@/components/feedback/ToastProvider';

interface TokenGeneratorProps {
  tokenType: 'webhook_secret' | 'api_token' | 'jwt_secret';
  label: string;
  onTokenGenerated?: (token: string) => void;
}

export function TokenGenerator({ tokenType, label, onTokenGenerated }: TokenGeneratorProps) {
  const [generating, setGenerating] = useState(false);
  const [newToken, setNewToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const generateToken = async () => {
    setGenerating(true);
    setError(null);
    setNewToken(null);

    try {
      const response = await configService.generateToken(tokenType);
      setNewToken(response.token);
      toast(`${label} generated successfully`, 'success');
      
      if (onTokenGenerated) {
        onTokenGenerated(response.token);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate token');
      toast(err.response?.data?.detail || 'Failed to generate token', 'error');
    } finally {
      setGenerating(false);
    }
  };

  const copyToClipboard = async () => {
    if (newToken) {
      await navigator.clipboard.writeText(newToken);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-4">
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={`Regenerate ${label}?`}
        description={`This will invalidate the current ${label.toLowerCase()}. Make sure you update any dependent services.`}
        variant="destructive"
        confirmText="Regenerate"
        onConfirm={() => generateToken()}
      />
      <div className="flex items-center gap-4">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setConfirmOpen(true)}
          disabled={generating}
        >
          {generating ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4 mr-2" />
              Regenerate {label}
            </>
          )}
        </Button>
      </div>

      {newToken && (
        <Alert>
          <AlertDescription>
            <p className="font-medium text-sm mb-2">New {label} generated:</p>
            <div className="flex items-center gap-2 bg-gray-50 p-3 rounded border">
              <code className="flex-1 text-xs font-mono break-all">{newToken}</code>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={copyToClipboard}
              >
                {copied ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-gray-600 mt-2">
              ⚠️ Make sure to save this token securely. It won't be shown again.
            </p>
          </AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}


