'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAuthStore } from '@/lib/store/auth';

interface Trial {
  id: string;
  user_name: string;
  user_telegram_id: number;
  status: 'active' | 'expired' | 'converted';
  duration_hours: number;
  ip_address: string;
  source: string;
  started_at: string;
  expires_at: string;
  converted_at?: string;
}

interface TrialSettings {
  is_enabled: boolean;
  duration_hours: number;
  max_devices: number;
  max_per_ip: number;
  max_per_fingerprint: number;
}

export default function TrialsPage() {
  const { token } = useAuthStore();
  const [trials, setTrials] = useState<Trial[]>([]);
  const [settings, setSettings] = useState<TrialSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    active: 0,
    expired: 0,
    converted: 0,
    conversion_rate: 0,
  });
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadTrials();
    loadSettings();
  }, [filter]);

  const loadTrials = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filter !== 'all') params.append('status', filter);

      const response = await fetch(`/api/v1/trial/admin/list?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setTrials(data.trials || []);
      setStats(data.stats || stats);
    } catch (error) {
      console.error('Failed to load trials:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSettings = async () => {
    try {
      const response = await fetch('/api/v1/trial/admin/settings', {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setSettings(data);
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const updateSettings = async (newSettings: Partial<TrialSettings>) => {
    try {
      await fetch('/api/v1/trial/admin/settings', {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newSettings),
      });
      loadSettings();
    } catch (error) {
      console.error('Failed to update settings:', error);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      active: 'bg-green-500/20 text-green-400',
      expired: 'bg-yellow-500/20 text-yellow-400',
      converted: 'bg-blue-500/20 text-blue-400',
    };
    const labels: Record<string, string> = {
      active: 'Активен',
      expired: 'Истёк',
      converted: 'Конверсия',
    };
    return <Badge className={colors[status]}>{labels[status]}</Badge>;
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">⏰ Пробные периоды</h1>
        <Button onClick={() => loadTrials()}>Обновить</Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-gray-400">Всего триалов</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-400">{stats.active}</div>
            <div className="text-sm text-gray-400">Активных</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-yellow-400">{stats.expired}</div>
            <div className="text-sm text-gray-400">Истёкших</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-blue-400">{stats.converted}</div>
            <div className="text-sm text-gray-400">Конверсий</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-purple-400">{stats.conversion_rate}%</div>
            <div className="text-sm text-gray-400">Конверсия</div>
          </CardContent>
        </Card>
      </div>

      {/* Settings */}
      {settings && (
        <Card>
          <CardHeader>
            <CardTitle>Настройки триала</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div>
                <label className="text-sm text-gray-400">Триал включён</label>
                <Button
                  variant={settings.is_enabled ? 'default' : 'outline'}
                  size="sm"
                  className="w-full mt-1"
                  onClick={() => updateSettings({ is_enabled: !settings.is_enabled })}
                >
                  {settings.is_enabled ? '✓ Включён' : 'Выключен'}
                </Button>
              </div>
              <div>
                <label className="text-sm text-gray-400">Длительность (ч)</label>
                <Input
                  type="number"
                  value={settings.duration_hours}
                  onChange={(e) => updateSettings({ duration_hours: parseInt(e.target.value) })}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400">Макс устройств</label>
                <Input
                  type="number"
                  value={settings.max_devices}
                  onChange={(e) => updateSettings({ max_devices: parseInt(e.target.value) })}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400">Макс на IP</label>
                <Input
                  type="number"
                  value={settings.max_per_ip}
                  onChange={(e) => updateSettings({ max_per_ip: parseInt(e.target.value) })}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400">Макс на fingerprint</label>
                <Input
                  type="number"
                  value={settings.max_per_fingerprint}
                  onChange={(e) => updateSettings({ max_per_fingerprint: parseInt(e.target.value) })}
                  className="mt-1"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <div className="flex gap-2">
        {['all', 'active', 'expired', 'converted'].map((f) => (
          <Button
            key={f}
            variant={filter === f ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter(f)}
          >
            {f === 'all' ? 'Все' : f === 'active' ? 'Активные' : f === 'expired' ? 'Истёкшие' : 'Конверсии'}
          </Button>
        ))}
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Пользователь</TableHead>
                <TableHead>Telegram ID</TableHead>
                <TableHead>IP</TableHead>
                <TableHead>Источник</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead>Начат</TableHead>
                <TableHead>Истекает</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    Загрузка...
                  </TableCell>
                </TableRow>
              ) : trials.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-gray-400">
                    Нет триалов
                  </TableCell>
                </TableRow>
              ) : (
                trials.map((trial) => (
                  <TableRow key={trial.id}>
                    <TableCell>{trial.user_name}</TableCell>
                    <TableCell className="font-mono">{trial.user_telegram_id}</TableCell>
                    <TableCell className="font-mono text-sm">{trial.ip_address}</TableCell>
                    <TableCell>{trial.source}</TableCell>
                    <TableCell>{getStatusBadge(trial.status)}</TableCell>
                    <TableCell className="text-sm">{formatDate(trial.started_at)}</TableCell>
                    <TableCell className="text-sm">{formatDate(trial.expires_at)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
