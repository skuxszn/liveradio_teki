/**
 * Individual setting field component.
 * Renders different input types based on value_type.
 */

import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/utils/cn';
import { type Setting } from '@/services/config.service';

interface SettingFieldProps {
  setting: Setting;
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

export function SettingField({ setting, value, onChange, error }: SettingFieldProps) {
  const [showPassword, setShowPassword] = useState(false);

  const renderInput = () => {
    const commonProps = {
      id: `${setting.category}.${setting.key}`,
      value: value || '',
      onChange: (e: React.ChangeEvent<HTMLInputElement>) => onChange(e.target.value),
      className: error ? 'border-red-500' : '',
    };

    // Debug logging - always log for important settings
    if (setting.key === 'FFMPEG_PRESET' || setting.key === 'VIDEO_BITRATE' || setting.key === 'AUDIO_BITRATE' || setting.key === 'VIDEO_RESOLUTION') {
      console.warn(`🔍 DEBUG ${setting.key}:`, {
        allowed_values: setting.allowed_values,
        type: typeof setting.allowed_values,
        isArray: Array.isArray(setting.allowed_values),
        length: setting.allowed_values?.length,
        fullSetting: setting
      });
    }

    // Dropdown/Select for settings with allowed_values - PLAIN HTML SELECT
    if (setting.allowed_values && Array.isArray(setting.allowed_values) && setting.allowed_values.length > 0) {
      return (
        <select
          id={`${setting.category}.${setting.key}`}
          value={value || setting.default_value || ''}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            error ? 'border-red-500' : ''
          )}
        >
          <option value="">Select {setting.key.toLowerCase()}...</option>
          {setting.allowed_values.map((option: string) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }

    // Secret fields (passwords, tokens, API keys)
    if (setting.is_secret) {
      return (
        <div className="relative">
          <Input
            {...commonProps}
            type={showPassword ? 'text' : 'password'}
            placeholder={setting.default_value || '••••••••'}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
          >
            {showPassword ? (
              <EyeOff className="w-4 h-4" />
            ) : (
              <Eye className="w-4 h-4" />
            )}
          </button>
        </div>
      );
    }

    // Number inputs
    if (setting.value_type === 'integer' || setting.value_type === 'float') {
      return (
        <Input
          {...commonProps}
          type="number"
          min={setting.validation_min || undefined}
          max={setting.validation_max || undefined}
          step={setting.value_type === 'float' ? '0.1' : '1'}
          placeholder={setting.default_value || undefined}
        />
      );
    }

    // URL inputs
    if (setting.value_type === 'url') {
      return (
        <Input
          {...commonProps}
          type="url"
          placeholder={setting.default_value || 'https://example.com'}
        />
      );
    }

    // Path inputs
    if (setting.value_type === 'path') {
      return (
        <Input
          {...commonProps}
          type="text"
          placeholder={setting.default_value || '/path/to/directory'}
        />
      );
    }

    // Boolean (handled separately with switch/toggle)
    if (setting.value_type === 'boolean') {
      return (
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id={commonProps.id}
            checked={value === 'true' || value === '1'}
            onChange={(e) => onChange(e.target.checked ? 'true' : 'false')}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <span className="text-sm text-gray-600">Enabled</span>
        </div>
      );
    }

    // Default: text input
    return (
      <Input
        {...commonProps}
        type="text"
        placeholder={setting.default_value || undefined}
      />
    );
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label htmlFor={`${setting.category}.${setting.key}`}>
          {setting.key}
          {setting.is_required && <span className="text-red-500 ml-1">*</span>}
        </Label>
        {setting.requires_restart && (
          <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
            Restart Required
          </span>
        )}
      </div>

      {setting.description && (
        <p className="text-sm text-gray-500">{setting.description}</p>
      )}

      {renderInput()}

      {error && <p className="text-sm text-red-500">{error}</p>}

      {setting.validation_regex && (
        <p className="text-xs text-gray-400">Pattern: {setting.validation_regex}</p>
      )}
    </div>
  );
}

