'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAuthStore } from '@/lib/store/auth';

interface GiftCertificate {
  id: string;
  code: string;
  buyer_name: string;
  buyer_telegram_id: number;
  recipient_name?: string;
  recipient_telegram_id?: number;
  plan_name: string;
  amount: number;
  status: 'active' | 'redeemed' | 'expired' | 'cancelled';
  created_at: string;
  expires_at: string;
  redeemed_at?: string;
}

export default function GiftsPage() {
  const { token } = useAuthStore();
  const [gifts, setGifts] = useState<GiftCertificate[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    active: 0,
    redeemed: 0,
    expired: 0,
    revenue: 0,
  });
  const [filter, setFilter] = useState<string>('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadGifts();
  }, [filter]);

  const loadGifts = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filter !== 'all') params.append('status', filter);
      if (search) params.append('search', search);

      const response = await fetch(`/api/v1/gifts/admin/list?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setGifts(data.certificates || []);
      setStats(data.stats || stats);
    } catch (error) {
      console.error('Failed to load gifts:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      active: 'bg-green-500/20 text-green-400',
      redeemed: 'bg-blue-500/20 text-blue-400',
      expired: 'bg-yellow-500/20 text-yellow-400',
      cancelled: 'bg-red-500/20 text-red-400',
    };
    const labels: Record<string, string> = {
      active: 'Активен',
      redeemed: 'Использован',
      expired: 'Истёк',
      cancelled: 'Отменён',
    };
    return <Badge className={colors[status]}>{labels[status]}</Badge>;
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">🎁 Подарочные сертификаты</h1>
        <Button onClick={() => loadGifts()}>Обновить</Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-gray-400">Всего</div>
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
            <div className="text-2xl font-bold text-blue-400">{stats.redeemed}</div>
            <div className="text-sm text-gray-400">Использовано</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-yellow-400">{stats.expired}</div>
            <div className="text-sm text-gray-400">Истекло</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.revenue}₽</div>
            <div className="text-sm text-gray-400">Выручка</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-4">
            <Input
              placeholder="Поиск по коду..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-xs"
            />
            <div className="flex gap-2">
              {['all', 'active', 'redeemed', 'expired'].map((f) => (
                <Button
                  key={f}
                  variant={filter === f ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFilter(f)}
                >
                  {f === 'all' ? 'Все' : f === 'active' ? 'Активные' : f === 'redeemed' ? 'Использованные' : 'Истёкшие'}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Код</TableHead>
                <TableHead>Покупатель</TableHead>
                <TableHead>Получатель</TableHead>
                <TableHead>Тариф</TableHead>
                <TableHead>Сумма</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead>Создан</TableHead>
                <TableHead>Истекает</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    Загрузка...
                  </TableCell>
                </TableRow>
              ) : gifts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-gray-400">
                    Нет сертификатов
                  </TableCell>
                </TableRow>
              ) : (
                gifts.map((gift) => (
                  <TableRow key={gift.id}>
                    <TableCell className="font-mono">{gift.code}</TableCell>
                    <TableCell>
                      <div>{gift.buyer_name}</div>
                      <div className="text-xs text-gray-400">{gift.buyer_telegram_id}</div>
                    </TableCell>
                    <TableCell>
                      {gift.recipient_name ? (
                        <>
                          <div>{gift.recipient_name}</div>
                          <div className="text-xs text-gray-400">{gift.recipient_telegram_id}</div>
                        </>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </TableCell>
                    <TableCell>{gift.plan_name}</TableCell>
                    <TableCell>{gift.amount}₽</TableCell>
                    <TableCell>{getStatusBadge(gift.status)}</TableCell>
                    <TableCell className="text-sm">{formatDate(gift.created_at)}</TableCell>
                    <TableCell className="text-sm">{formatDate(gift.expires_at)}</TableCell>
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
