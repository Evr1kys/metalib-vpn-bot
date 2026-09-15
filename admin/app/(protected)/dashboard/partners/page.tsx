'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAuthStore } from '@/lib/store/auth';

interface Partner {
  id: string;
  user_name: string;
  user_telegram_id: number;
  referral_code: string;
  status: 'pending' | 'active' | 'suspended' | 'rejected';
  tier: 'bronze' | 'silver' | 'gold' | 'platinum';
  commission_percent: number;
  telegram_channel?: string;
  website?: string;
  total_clicks: number;
  total_sales: number;
  total_earned: number;
  pending_payout: number;
  created_at: string;
}

interface PartnerPayout {
  id: string;
  partner_name: string;
  amount: number;
  method: string;
  status: 'pending' | 'processing' | 'completed' | 'rejected';
  created_at: string;
}

export default function PartnersPage() {
  const { token } = useAuthStore();
  const [partners, setPartners] = useState<Partner[]>([]);
  const [payouts, setPayouts] = useState<PartnerPayout[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'partners' | 'payouts' | 'applications'>('partners');
  const [stats, setStats] = useState({
    total_partners: 0,
    active_partners: 0,
    pending_applications: 0,
    total_revenue: 0,
    pending_payouts: 0,
  });
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadPartners();
    loadPayouts();
  }, [filter]);

  const loadPartners = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filter !== 'all') params.append('status', filter);

      const response = await fetch(`/api/v1/partners/admin/list?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setPartners(data.partners || []);
      setStats(data.stats || stats);
    } catch (error) {
      console.error('Failed to load partners:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPayouts = async () => {
    try {
      const response = await fetch('/api/v1/partners/admin/payouts', {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setPayouts(data.payouts || []);
    } catch (error) {
      console.error('Failed to load payouts:', error);
    }
  };

  const approvePartner = async (partnerId: string) => {
    try {
      await fetch(`/api/v1/partners/admin/${partnerId}/approve`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      loadPartners();
    } catch (error) {
      console.error('Failed to approve partner:', error);
    }
  };

  const rejectPartner = async (partnerId: string) => {
    try {
      await fetch(`/api/v1/partners/admin/${partnerId}/reject`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      loadPartners();
    } catch (error) {
      console.error('Failed to reject partner:', error);
    }
  };

  const processPayout = async (payoutId: string, action: 'approve' | 'reject') => {
    try {
      await fetch(`/api/v1/partners/admin/payouts/${payoutId}/${action}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      loadPayouts();
      loadPartners();
    } catch (error) {
      console.error('Failed to process payout:', error);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-500/20 text-yellow-400',
      active: 'bg-green-500/20 text-green-400',
      suspended: 'bg-red-500/20 text-red-400',
      rejected: 'bg-gray-500/20 text-gray-400',
      processing: 'bg-blue-500/20 text-blue-400',
      completed: 'bg-green-500/20 text-green-400',
    };
    const labels: Record<string, string> = {
      pending: 'Ожидает',
      active: 'Активен',
      suspended: 'Заблокирован',
      rejected: 'Отклонён',
      processing: 'В обработке',
      completed: 'Завершён',
    };
    return <Badge className={colors[status]}>{labels[status]}</Badge>;
  };

  const getTierBadge = (tier: string) => {
    const colors: Record<string, string> = {
      bronze: 'bg-amber-700/20 text-amber-400',
      silver: 'bg-gray-400/20 text-gray-300',
      gold: 'bg-yellow-500/20 text-yellow-400',
      platinum: 'bg-purple-500/20 text-purple-400',
    };
    const labels: Record<string, string> = {
      bronze: '🥉 Bronze',
      silver: '🥈 Silver',
      gold: '🥇 Gold',
      platinum: '💎 Platinum',
    };
    return <Badge className={colors[tier]}>{labels[tier]}</Badge>;
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">🤝 Партнёрская программа</h1>
        <Button onClick={() => loadPartners()}>Обновить</Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.total_partners}</div>
            <div className="text-sm text-gray-400">Всего партнёров</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-400">{stats.active_partners}</div>
            <div className="text-sm text-gray-400">Активных</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-yellow-400">{stats.pending_applications}</div>
            <div className="text-sm text-gray-400">Заявок</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.total_revenue}₽</div>
            <div className="text-sm text-gray-400">Выплачено</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-orange-400">{stats.pending_payouts}₽</div>
            <div className="text-sm text-gray-400">К выплате</div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-700 pb-2">
        <Button
          variant={activeTab === 'partners' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('partners')}
        >
          Партнёры
        </Button>
        <Button
          variant={activeTab === 'applications' ? 'default' : 'ghost'}
          onClick={() => { setActiveTab('applications'); setFilter('pending'); }}
        >
          Заявки ({stats.pending_applications})
        </Button>
        <Button
          variant={activeTab === 'payouts' ? 'default' : 'ghost'}
          onClick={() => setActiveTab('payouts')}
        >
          Выплаты
        </Button>
      </div>

      {/* Partners Table */}
      {activeTab === 'partners' && (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Партнёр</TableHead>
                  <TableHead>Реф. код</TableHead>
                  <TableHead>Статус</TableHead>
                  <TableHead>Уровень</TableHead>
                  <TableHead>Комиссия</TableHead>
                  <TableHead>Клики</TableHead>
                  <TableHead>Продажи</TableHead>
                  <TableHead>Заработано</TableHead>
                  <TableHead>К выплате</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8">
                      Загрузка...
                    </TableCell>
                  </TableRow>
                ) : partners.filter(p => p.status === 'active').length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-gray-400">
                      Нет активных партнёров
                    </TableCell>
                  </TableRow>
                ) : (
                  partners.filter(p => p.status === 'active').map((partner) => (
                    <TableRow key={partner.id}>
                      <TableCell>
                        <div>{partner.user_name}</div>
                        <div className="text-xs text-gray-400">{partner.user_telegram_id}</div>
                      </TableCell>
                      <TableCell className="font-mono">{partner.referral_code}</TableCell>
                      <TableCell>{getStatusBadge(partner.status)}</TableCell>
                      <TableCell>{getTierBadge(partner.tier)}</TableCell>
                      <TableCell>{partner.commission_percent}%</TableCell>
                      <TableCell>{partner.total_clicks}</TableCell>
                      <TableCell>{partner.total_sales}</TableCell>
                      <TableCell>{partner.total_earned}₽</TableCell>
                      <TableCell>{partner.pending_payout}₽</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Applications Table */}
      {activeTab === 'applications' && (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Заявитель</TableHead>
                  <TableHead>Telegram</TableHead>
                  <TableHead>Канал</TableHead>
                  <TableHead>Сайт</TableHead>
                  <TableHead>Дата</TableHead>
                  <TableHead>Действия</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {partners.filter(p => p.status === 'pending').length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-gray-400">
                      Нет заявок
                    </TableCell>
                  </TableRow>
                ) : (
                  partners.filter(p => p.status === 'pending').map((partner) => (
                    <TableRow key={partner.id}>
                      <TableCell>{partner.user_name}</TableCell>
                      <TableCell className="font-mono">{partner.user_telegram_id}</TableCell>
                      <TableCell>
                        {partner.telegram_channel ? (
                          <a href={partner.telegram_channel} target="_blank" className="text-blue-400 hover:underline">
                            {partner.telegram_channel}
                          </a>
                        ) : '—'}
                      </TableCell>
                      <TableCell>
                        {partner.website ? (
                          <a href={partner.website} target="_blank" className="text-blue-400 hover:underline">
                            {partner.website}
                          </a>
                        ) : '—'}
                      </TableCell>
                      <TableCell>{formatDate(partner.created_at)}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <Button size="sm" onClick={() => approvePartner(partner.id)}>
                            ✓ Принять
                          </Button>
                          <Button size="sm" variant="destructive" onClick={() => rejectPartner(partner.id)}>
                            ✕ Отклонить
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Payouts Table */}
      {activeTab === 'payouts' && (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Партнёр</TableHead>
                  <TableHead>Сумма</TableHead>
                  <TableHead>Способ</TableHead>
                  <TableHead>Статус</TableHead>
                  <TableHead>Дата</TableHead>
                  <TableHead>Действия</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payouts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-8 text-gray-400">
                      Нет заявок на выплату
                    </TableCell>
                  </TableRow>
                ) : (
                  payouts.map((payout) => (
                    <TableRow key={payout.id}>
                      <TableCell>{payout.partner_name}</TableCell>
                      <TableCell>{payout.amount}₽</TableCell>
                      <TableCell>{payout.method}</TableCell>
                      <TableCell>{getStatusBadge(payout.status)}</TableCell>
                      <TableCell>{formatDate(payout.created_at)}</TableCell>
                      <TableCell>
                        {payout.status === 'pending' && (
                          <div className="flex gap-2">
                            <Button size="sm" onClick={() => processPayout(payout.id, 'approve')}>
                              ✓ Выплатить
                            </Button>
                            <Button size="sm" variant="destructive" onClick={() => processPayout(payout.id, 'reject')}>
                              ✕ Отклонить
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
