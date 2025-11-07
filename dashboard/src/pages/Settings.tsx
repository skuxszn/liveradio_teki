/**
 * Settings & Configuration page.
 * Complete settings management interface organized by category.
 */

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Save, RotateCcw, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { SettingsSection } from '@/components/settings/SettingsSection';
import { SettingField } from '@/components/settings/SettingField';
import { ConnectionTester } from '@/components/settings/ConnectionTester';
import { TokenGenerator } from '@/components/settings/TokenGenerator';
import configService, { type Setting } from '@/services/config.service';

interface SettingValues {
  [key: string]: string;
}

interface SettingErrors {
  [key: string]: string;
}

export default function Settings() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('stream');
  const [settingValues, setSettingValues] = useState<SettingValues>({});
  const [errors, setErrors] = useState<SettingErrors>({});
  const [isDirty, setIsDirty] = useState(false);
  const [requiresRestart, setRequiresRestart] = useState(false);

  // Fetch all settings
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => configService.getAll(),
  });

  // Initialize setting values when data loads
  useEffect(() => {
    if (settings) {
      const values: SettingValues = {};
      settings.forEach((setting) => {
        const key = `${setting.category}.${setting.key}`;
        values[key] = setting.value || setting.default_value || '';
      });
      setSettingValues(values);
    }
  }, [settings]);

  // Mutation for bulk update
  const updateMutation = useMutation({
    mutationFn: (updates: Record<string, string>) =>
      configService.bulkUpdate(updates),
    onSuccess: (result) => {
      // Invalidate settings query
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      setIsDirty(false);

      if (result.error_count === 0) {
        alert('Settings updated successfully!');
      } else {
        alert(`Settings updated with ${result.error_count} errors. Check the console for details.`);
        console.error('Update errors:', result.errors);
      }
    },
    onError: (error: any) => {
      alert(`Failed to update settings: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Handle setting value change
  const handleSettingChange = (setting: Setting, newValue: string) => {
    const key = `${setting.category}.${setting.key}`;
    setSettingValues((prev) => ({ ...prev, [key]: newValue }));
    setIsDirty(true);

    if (setting.requires_restart) {
      setRequiresRestart(true);
    }

    // Validate the value
    validateSetting(setting, newValue);
  };

  // Validate a single setting
  const validateSetting = (setting: Setting, value: string, skipRequiredCheck = false): boolean => {
    const key = `${setting.category}.${setting.key}`;
    let error = '';

    // Required validation - only check if not skipping and value is truly empty
    // Skip required check for fields that haven't been modified (still have default/original value)
    if (!skipRequiredCheck && setting.is_required && !value && value !== setting.default_value) {
      error = 'This field is required';
    }

    // Only validate format/pattern if there's actually a value
    if (value) {
      // Regex validation
      if (setting.validation_regex) {
        const regex = new RegExp(setting.validation_regex);
        if (!regex.test(value)) {
          error = `Value does not match required pattern`;
        }
      }

      // Numeric validation
      if (setting.value_type === 'integer' || setting.value_type === 'float') {
        const num = parseFloat(value);
        if (isNaN(num)) {
          error = 'Must be a valid number';
        } else {
          if (setting.validation_min !== null && num < setting.validation_min) {
            error = `Must be at least ${setting.validation_min}`;
          }
          if (setting.validation_max !== null && num > setting.validation_max) {
            error = `Must be at most ${setting.validation_max}`;
          }
        }
      }

      // URL validation
      if (setting.value_type === 'url') {
        try {
          new URL(value);
        } catch {
          error = 'Must be a valid URL';
        }
      }
    }

    setErrors((prev) => ({ ...prev, [key]: error }));
    return !error;
  };

  // Handle save
  const handleSave = () => {
    // Only validate settings that have been changed or have values
    let hasErrors = false;
    if (settings) {
      settings.forEach((setting) => {
        const key = `${setting.category}.${setting.key}`;
        const newValue = settingValues[key];
        const oldValue = setting.value || setting.default_value || '';
        
        // Only validate if the value has changed or if there's a value
        if (newValue !== oldValue || newValue) {
          // Skip required check for unchanged empty fields
          const skipRequired = (newValue === oldValue && !newValue);
          if (!validateSetting(setting, newValue, skipRequired)) {
            hasErrors = true;
          }
        }
      });
    }

    if (hasErrors) {
      alert('Please fix validation errors before saving');
      return;
    }

    // Only send changed values
    const updates: Record<string, string> = {};
    if (settings) {
      settings.forEach((setting) => {
        const key = `${setting.category}.${setting.key}`;
        const newValue = settingValues[key];
        const oldValue = setting.value || setting.default_value || '';
        
        if (newValue !== oldValue) {
          updates[key] = newValue;
        }
      });
    }

    if (Object.keys(updates).length === 0) {
      alert('No changes to save');
      return;
    }

    updateMutation.mutate(updates);
  };

  // Handle reset
  const handleReset = () => {
    if (!confirm('Are you sure you want to reset all settings to their current saved values?')) {
      return;
    }

    if (settings) {
      const values: SettingValues = {};
      settings.forEach((setting) => {
        const key = `${setting.category}.${setting.key}`;
        values[key] = setting.value || setting.default_value || '';
      });
      setSettingValues(values);
      setIsDirty(false);
      setRequiresRestart(false);
      setErrors({});
    }
  };

  // Get settings for a specific category
  const getSettingsByCategory = (category: string): Setting[] => {
    return settings?.filter((s) => s.category === category) || [];
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gray-500">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-gray-500">Configure your radio stream</p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleReset}
            disabled={!isDirty || updateMutation.isPending}
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </Button>
          <Button
            onClick={handleSave}
            disabled={!isDirty || updateMutation.isPending || Object.values(errors).some(Boolean)}
          >
            <Save className="w-4 h-4 mr-2" />
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {requiresRestart && isDirty && (
        <Alert>
          <AlertTriangle className="w-4 h-4" />
          <AlertDescription>
            Some changed settings require a stream restart to take effect.
          </AlertDescription>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList>
          <TabsTrigger value="stream">Stream</TabsTrigger>
          <TabsTrigger value="encoding">Encoding</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="database">Database</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="paths">Paths</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
        </TabsList>

        <TabsContent value="stream" className="space-y-6">
          <SettingsSection
            title="Stream Configuration"
            description="Configure YouTube and AzuraCast stream settings"
          >
            {getSettingsByCategory('stream').map((setting) => (
              <SettingField
                key={setting.id}
                setting={setting}
                value={settingValues[`${setting.category}.${setting.key}`] || ''}
                onChange={(value) => handleSettingChange(setting, value)}
                error={errors[`${setting.category}.${setting.key}`]}
              />
            ))}

            <div className="pt-4 border-t">
              <h4 className="font-medium mb-4">Connection Test</h4>
              <ConnectionTester />
            </div>
          </SettingsSection>
        </TabsContent>

        <TabsContent value="encoding" className="space-y-6">
          <SettingsSection
            title="Encoding Settings"
            description="Configure video and audio encoding parameters"
          >
            {getSettingsByCategory('encoding').map((setting) => (
              <SettingField
                key={setting.id}
                setting={setting}
                value={settingValues[`${setting.category}.${setting.key}`] || ''}
                onChange={(value) => handleSettingChange(setting, value)}
                error={errors[`${setting.category}.${setting.key}`]}
              />
            ))}
          </SettingsSection>
        </TabsContent>

        <TabsContent value="notifications" className="space-y-6">
          <SettingsSection
            title="Notification Settings"
            description="Configure Discord and Slack webhooks for notifications"
          >
            {getSettingsByCategory('notifications').map((setting) => (
              <SettingField
                key={setting.id}
                setting={setting}
                value={settingValues[`${setting.category}.${setting.key}`] || ''}
                onChange={(value) => handleSettingChange(setting, value)}
                error={errors[`${setting.category}.${setting.key}`]}
              />
            ))}
          </SettingsSection>
        </TabsContent>

        <TabsContent value="database" className="space-y-6">
          <SettingsSection
            title="Database Settings"
            description="Configure PostgreSQL connection"
          >
            {getSettingsByCategory('database').map((setting) => (
              <SettingField
                key={setting.id}
                setting={setting}
                value={settingValues[`${setting.category}.${setting.key}`] || ''}
                onChange={(value) => handleSettingChange(setting, value)}
                error={errors[`${setting.category}.${setting.key}`]}
              />
            ))}
          </SettingsSection>
        </TabsContent>

        <TabsContent value="security" className="space-y-6">
          <SettingsSection
            title="Security Settings"
            description="Manage security tokens and API keys"
          >
            {getSettingsByCategory('security').map((setting) => (
              <div key={setting.id} className="space-y-4">
                <SettingField
                  setting={setting}
                  value={settingValues[`${setting.category}.${setting.key}`] || ''}
                  onChange={(value) => handleSettingChange(setting, value)}
                  error={errors[`${setting.category}.${setting.key}`]}
                />
                
                {/* Add token generator for specific keys */}
                {setting.key === 'WEBHOOK_SECRET' && (
                  <TokenGenerator
                    tokenType="webhook_secret"
                    label="Webhook Secret"
                    onTokenGenerated={(token) =>
                      handleSettingChange(setting, token)
                    }
                  />
                )}
                {setting.key === 'API_TOKEN' && (
                  <TokenGenerator
                    tokenType="api_token"
                    label="API Token"
                    onTokenGenerated={(token) =>
                      handleSettingChange(setting, token)
                    }
                  />
                )}
                {setting.key === 'JWT_SECRET' && (
                  <TokenGenerator
                    tokenType="jwt_secret"
                    label="JWT Secret"
                    onTokenGenerated={(token) =>
                      handleSettingChange(setting, token)
                    }
                  />
                )}
              </div>
            ))}
          </SettingsSection>
        </TabsContent>

        <TabsContent value="paths" className="space-y-6">
          <SettingsSection
            title="Path Settings"
            description="Configure file and directory paths"
          >
            {getSettingsByCategory('paths').map((setting) => (
              <SettingField
                key={setting.id}
                setting={setting}
                value={settingValues[`${setting.category}.${setting.key}`] || ''}
                onChange={(value) => handleSettingChange(setting, value)}
                error={errors[`${setting.category}.${setting.key}`]}
              />
            ))}
          </SettingsSection>
        </TabsContent>

        <TabsContent value="advanced" className="space-y-6">
          <SettingsSection
            title="Advanced Settings"
            description="Advanced configuration options"
          >
            {getSettingsByCategory('advanced').map((setting) => (
              <SettingField
                key={setting.id}
                setting={setting}
                value={settingValues[`${setting.category}.${setting.key}`] || ''}
                onChange={(value) => handleSettingChange(setting, value)}
                error={errors[`${setting.category}.${setting.key}`]}
              />
            ))}
          </SettingsSection>
        </TabsContent>
      </Tabs>
    </div>
  );
}
