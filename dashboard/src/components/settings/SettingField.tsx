/**
 * Individual setting field component.
 * Renders different input types based on value_type.
 */

import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { type Setting } from '@/services/config.service';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { HelpTooltip } from './HelpTooltip';

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

    if (setting.allowed_values && Array.isArray(setting.allowed_values) && setting.allowed_values.length > 0) {
      return (
        <Select value={value || setting.default_value || ''} onValueChange={onChange}>
          <SelectTrigger>
            <SelectValue placeholder={`Select ${setting.key.toLowerCase()}...`} />
          </SelectTrigger>
          <SelectContent>
            {setting.allowed_values.map((option: string) => (
              <SelectItem key={option} value={option}>{option}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
    }

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
            aria-label={showPassword ? 'Hide value' : 'Show value'}
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

    if (setting.value_type === 'url') {
      return (
        <Input
          {...commonProps}
          type="url"
          placeholder={setting.default_value || 'https://example.com'}
        />
      );
    }

    if (setting.value_type === 'path') {
      return (
        <Input
          {...commonProps}
          type="text"
          placeholder={setting.default_value || '/path/to/directory'}
        />
      );
    }

    if (setting.value_type === 'boolean') {
      const checked = value === 'true' || value === '1'
      return (
        <div className="flex items-center gap-2">
          <Switch checked={checked} onCheckedChange={(v) => onChange(v ? 'true' : 'false')} />
          <span className="text-sm text-gray-600">{checked ? 'Enabled' : 'Disabled'}</span>
        </div>
      );
    }

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
        <div className="flex items-center gap-2">
          <Label htmlFor={`${setting.category}.${setting.key}`}>
            {setting.key}
            {setting.is_required && <span className="text-red-500 ml-1">*</span>}
          </Label>
          {(setting.description || setting.validation_regex) && (
            <HelpTooltip text={setting.description || 'Enter a value matching the required format.'} />
          )}
        </div>
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
        <p className="text-xs text-gray-500">Example format: see tooltip. Pattern: <code className="text-[10px]">{setting.validation_regex}</code></p>
      )}
      {(setting.value_type === 'integer' || setting.value_type === 'float') && (setting.validation_min !== null || setting.validation_max !== null) && (
        <p className="text-xs text-gray-500">Allowed range: {setting.validation_min !== null ? setting.validation_min : '—'} to {setting.validation_max !== null ? setting.validation_max : '—'}</p>
      )}
      {setting.value_type === 'url' && (
        <p className="text-xs text-gray-500">Example: https://your-azuracast.example.com</p>
      )}
      {setting.value_type === 'path' && (
        <p className="text-xs text-gray-500">Use absolute paths where possible, e.g., /srv/loops</p>
      )}
    </div>
  );
}

