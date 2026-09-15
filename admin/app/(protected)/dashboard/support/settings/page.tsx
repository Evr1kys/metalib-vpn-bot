'use client';

import { useState, useEffect } from 'react';
import { 
  Settings, 
  Save, 
  Clock,
  MessageCircle,
  Bell,
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';

interface SupportSettings {
  auto_reply_enabled: boolean;
  auto_reply_message: string;
  working_hours_enabled: boolean;
  working_hours_start: string;
  working_hours_end: string;
  working_hours_timezone: string;
  outside_hours_message: string;
  notify_new_ticket: boolean;
  notify_new_message: boolean;
}

export default function SupportSettingsPage() {
  const [settings, setSettings] = useState<SupportSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await api.get('/support/settings');
      setSettings(response.data);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    if (!settings) return;
    
    setSaving(true);
    try {
      await api.patch('/support/settings', settings);
      alert('Настройки сохранены');
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  if (loading || !settings) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 animate-spin text-purple-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500">
              <Settings className="w-6 h-6 text-white" />
            </div>
            Настройки поддержки
          </h1>
          <p className="text-gray-400 mt-1">Настройка автоответов и уведомлений</p>
        </div>
        <Button
          onClick={saveSettings}
          disabled={saving}
          className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
        >
          {saving ? (
            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          Сохранить
        </Button>
      </div>

      {/* Auto-reply */}
      <Card className="bg-gray-800/50 border-gray-700/50">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-purple-400" />
            Автоответ
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="auto_reply_enabled"
              checked={settings.auto_reply_enabled}
              onChange={(e) => setSettings({...settings, auto_reply_enabled: e.target.checked})}
              className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-purple-500 focus:ring-purple-500"
            />
            <label htmlFor="auto_reply_enabled" className="text-white">
              Автоматический ответ на новые обращения
            </label>
          </div>
          
          {settings.auto_reply_enabled && (
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                Текст автоответа
              </label>
              <textarea
                value={settings.auto_reply_message}
                onChange={(e) => setSettings({...settings, auto_reply_message: e.target.value})}
                rows={3}
                className="w-full p-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white resize-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                placeholder="Спасибо за обращение! Наш специалист ответит вам в ближайшее время."
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Working hours */}
      <Card className="bg-gray-800/50 border-gray-700/50">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Clock className="w-5 h-5 text-blue-400" />
            Рабочее время
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="working_hours_enabled"
              checked={settings.working_hours_enabled}
              onChange={(e) => setSettings({...settings, working_hours_enabled: e.target.checked})}
              className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-purple-500 focus:ring-purple-500"
            />
            <label htmlFor="working_hours_enabled" className="text-white">
              Ограничить часы поддержки
            </label>
          </div>
          
          {settings.working_hours_enabled && (
            <>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    Начало
                  </label>
                  <Input
                    type="time"
                    value={settings.working_hours_start}
                    onChange={(e) => setSettings({...settings, working_hours_start: e.target.value})}
                    className="bg-gray-900/50 border-gray-600"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    Конец
                  </label>
                  <Input
                    type="time"
                    value={settings.working_hours_end}
                    onChange={(e) => setSettings({...settings, working_hours_end: e.target.value})}
                    className="bg-gray-900/50 border-gray-600"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    Часовой пояс
                  </label>
                  <Input
                    value={settings.working_hours_timezone}
                    onChange={(e) => setSettings({...settings, working_hours_timezone: e.target.value})}
                    className="bg-gray-900/50 border-gray-600"
                    placeholder="Europe/Moscow"
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Сообщение вне рабочего времени
                </label>
                <textarea
                  value={settings.outside_hours_message}
                  onChange={(e) => setSettings({...settings, outside_hours_message: e.target.value})}
                  rows={2}
                  className="w-full p-3 bg-gray-900/50 border border-gray-600 rounded-lg text-white resize-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                  placeholder="Сейчас нерабочее время. Мы ответим вам в рабочие часы."
                />
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card className="bg-gray-800/50 border-gray-700/50">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Bell className="w-5 h-5 text-yellow-400" />
            Уведомления
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="notify_new_ticket"
              checked={settings.notify_new_ticket}
              onChange={(e) => setSettings({...settings, notify_new_ticket: e.target.checked})}
              className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-purple-500 focus:ring-purple-500"
            />
            <label htmlFor="notify_new_ticket" className="text-white">
              Уведомлять о новых обращениях
            </label>
          </div>
          
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="notify_new_message"
              checked={settings.notify_new_message}
              onChange={(e) => setSettings({...settings, notify_new_message: e.target.checked})}
              className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-purple-500 focus:ring-purple-500"
            />
            <label htmlFor="notify_new_message" className="text-white">
              Уведомлять о новых сообщениях
            </label>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
