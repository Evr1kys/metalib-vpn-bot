'use client';

import { useState, useEffect, useRef } from 'react';
import { 
  MessageCircle, 
  Search, 
  Send, 
  User, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  Filter,
  RefreshCw,
  ChevronRight,
  Circle,
  ArrowLeft,
  Settings,
  MoreVertical
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';

interface Message {
  id: string;
  ticket_id: string;
  sender_type: 'user' | 'admin' | 'system';
  sender_admin_id?: string;
  sender_admin_name?: string;
  text?: string;
  attachments?: any[];
  is_read: boolean;
  delivered_at?: string;
  created_at: string;
}

interface Ticket {
  id: string;
  user_id?: string;
  telegram_user_id: number;
  telegram_username?: string;
  telegram_first_name?: string;
  telegram_last_name?: string;
  subject?: string;
  status: 'open' | 'in_progress' | 'waiting_user' | 'resolved' | 'closed';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  assigned_admin_id?: string;
  assigned_admin_name?: string;
  created_at: string;
  updated_at: string;
  last_message_at: string;
  resolved_at?: string;
  message_count: number;
  unread_count: number;
  last_message?: Message;
  messages?: Message[];
}

interface SupportStats {
  total_tickets: number;
  open_tickets: number;
  in_progress_tickets: number;
  resolved_today: number;
  avg_response_time_minutes?: number;
  unread_messages: number;
}

const statusConfig = {
  open: { label: 'Открыт', color: 'bg-green-500', textColor: 'text-green-400' },
  in_progress: { label: 'В работе', color: 'bg-blue-500', textColor: 'text-blue-400' },
  waiting_user: { label: 'Ожидает ответа', color: 'bg-yellow-500', textColor: 'text-yellow-400' },
  resolved: { label: 'Решён', color: 'bg-gray-500', textColor: 'text-gray-400' },
  closed: { label: 'Закрыт', color: 'bg-gray-600', textColor: 'text-gray-500' },
};

const priorityConfig = {
  low: { label: 'Низкий', color: 'text-gray-400' },
  normal: { label: 'Обычный', color: 'text-blue-400' },
  high: { label: 'Высокий', color: 'text-orange-400' },
  urgent: { label: 'Срочный', color: 'text-red-400' },
};

export default function SupportPage() {
  const [stats, setStats] = useState<SupportStats | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(true);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [messageText, setMessageText] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [statusFilter]);

  useEffect(() => {
    scrollToBottom();
  }, [selectedTicket?.messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchData = async () => {
    try {
      const [statsRes, ticketsRes] = await Promise.all([
        api.get('/support/stats'),
        api.get('/support/tickets', {
          params: {
            status: statusFilter || undefined,
            search: searchQuery || undefined,
          }
        })
      ]);
      console.log('Stats response:', statsRes.data);
      console.log('Tickets response:', ticketsRes.data);
      setStats(statsRes.data);
      setTickets(ticketsRes.data.tickets || []);
    } catch (error) {
      console.error('Failed to fetch support data:', error);
    } finally {
      setLoading(false);
    }
  };

  const selectTicket = async (ticket: Ticket) => {
    try {
      const response = await api.get(`/support/tickets/${ticket.id}`);
      setSelectedTicket(response.data);
      // Update ticket in list to show read status
      setTickets(prev => prev.map(t => 
        t.id === ticket.id ? { ...t, unread_count: 0 } : t
      ));
    } catch (error) {
      console.error('Failed to fetch ticket:', error);
    }
  };

  const sendMessage = async () => {
    if (!selectedTicket || !messageText.trim()) return;
    
    setSendingMessage(true);
    try {
      const response = await api.post(`/support/tickets/${selectedTicket.id}/messages`, {
        text: messageText.trim()
      });
      
      // Add message to current view
      setSelectedTicket(prev => prev ? {
        ...prev,
        messages: [...(prev.messages || []), response.data],
        status: 'waiting_user' as const,
        message_count: prev.message_count + 1,
      } : null);
      
      setMessageText('');
      
      // Update ticket in list
      setTickets(prev => prev.map(t => 
        t.id === selectedTicket.id ? {
          ...t,
          status: 'waiting_user' as const,
          last_message_at: new Date().toISOString(),
          message_count: t.message_count + 1,
        } : t
      ));
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setSendingMessage(false);
    }
  };

  const updateTicketStatus = async (status: string) => {
    if (!selectedTicket) return;
    
    try {
      await api.patch(`/support/tickets/${selectedTicket.id}`, { status });
      setSelectedTicket(prev => prev ? { ...prev, status: status as any } : null);
      setTickets(prev => prev.map(t => 
        t.id === selectedTicket.id ? { ...t, status: status as any } : t
      ));
    } catch (error) {
      console.error('Failed to update ticket:', error);
    }
  };

  const assignToMe = async () => {
    if (!selectedTicket) return;
    
    try {
      await api.post(`/support/tickets/${selectedTicket.id}/assign-me`);
      fetchData();
      if (selectedTicket) {
        selectTicket(selectedTicket);
      }
    } catch (error) {
      console.error('Failed to assign ticket:', error);
    }
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Только что';
    if (diffMins < 60) return `${diffMins} мин назад`;
    if (diffHours < 24) return `${diffHours} ч назад`;
    if (diffDays < 7) return `${diffDays} дн назад`;
    return date.toLocaleDateString('ru-RU');
  };

  const formatMessageTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  };

  const getUserDisplayName = (ticket: Ticket) => {
    if (ticket.telegram_first_name) {
      return ticket.telegram_last_name 
        ? `${ticket.telegram_first_name} ${ticket.telegram_last_name}`
        : ticket.telegram_first_name;
    }
    return ticket.telegram_username || `User ${ticket.telegram_user_id}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 animate-spin text-purple-500" />
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500">
            <MessageCircle className="w-6 h-6 text-white" />
          </div>
          Тикеты поддержки
        </h1>
        <p className="text-gray-400 mt-1">Управление обращениями пользователей</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Card className="bg-gray-800/50 border-gray-700/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">Открытых</p>
                <p className="text-2xl font-bold text-green-400">{stats?.open_tickets || 0}</p>
              </div>
              <Circle className="w-8 h-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gray-800/50 border-gray-700/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">В работе</p>
                <p className="text-2xl font-bold text-blue-400">{stats?.in_progress_tickets || 0}</p>
              </div>
              <Clock className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gray-800/50 border-gray-700/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">Решено сегодня</p>
                <p className="text-2xl font-bold text-purple-400">{stats?.resolved_today || 0}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-gray-800/50 border-gray-700/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">Непрочитанных</p>
                <p className="text-2xl font-bold text-orange-400">{stats?.unread_messages || 0}</p>
              </div>
              <AlertCircle className="w-8 h-8 text-orange-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Tickets List */}
        <Card className="w-96 flex flex-col bg-gray-800/50 border-gray-700/50">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Поиск..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && fetchData()}
                  className="pl-9 bg-gray-900/50 border-gray-600"
                />
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={fetchData}
                className="border-gray-600"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
            
            {/* Status Filter */}
            <div className="flex gap-1 mt-2 flex-wrap">
              {[
                { value: '', label: 'Все' },
                { value: 'open', label: 'Открытые' },
                { value: 'in_progress', label: 'В работе' },
                { value: 'waiting_user', label: 'Ожидание' },
              ].map(filter => (
                <Button
                  key={filter.value}
                  size="sm"
                  variant={statusFilter === filter.value ? 'default' : 'outline'}
                  onClick={() => setStatusFilter(filter.value)}
                  className={`text-xs ${statusFilter === filter.value 
                    ? 'bg-purple-600 hover:bg-purple-700' 
                    : 'border-gray-600 hover:bg-gray-700'}`}
                >
                  {filter.label}
                </Button>
              ))}
            </div>
          </CardHeader>
          
          <CardContent className="flex-1 overflow-y-auto p-2 space-y-2">
            {tickets.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                Нет обращений
              </div>
            ) : (
              tickets.map(ticket => (
                <div
                  key={ticket.id}
                  onClick={() => selectTicket(ticket)}
                  className={`p-3 rounded-lg cursor-pointer transition-all ${
                    selectedTicket?.id === ticket.id
                      ? 'bg-purple-600/20 border border-purple-500/50'
                      : 'bg-gray-900/50 hover:bg-gray-700/50 border border-transparent'
                  }`}
                >
                  <div className="flex items-start justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-sm font-medium">
                        {(ticket.telegram_first_name?.[0] || ticket.telegram_username?.[0] || 'U').toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">
                          {getUserDisplayName(ticket)}
                        </p>
                        {ticket.telegram_username && (
                          <p className="text-xs text-gray-500">@{ticket.telegram_username}</p>
                        )}
                      </div>
                    </div>
                    {ticket.unread_count > 0 && (
                      <span className="px-2 py-0.5 bg-purple-600 text-white text-xs rounded-full">
                        {ticket.unread_count}
                      </span>
                    )}
                  </div>
                  
                  <p className="text-sm text-gray-300 line-clamp-2 mb-2">
                    {ticket.last_message?.text || ticket.subject || 'Новое обращение'}
                  </p>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${statusConfig[ticket.status]?.color}`} />
                      <span className={`text-xs ${statusConfig[ticket.status]?.textColor}`}>
                        {statusConfig[ticket.status]?.label}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {formatTime(ticket.last_message_at)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Chat Area */}
        <Card className="flex-1 flex flex-col bg-gray-800/50 border-gray-700/50">
          {selectedTicket ? (
            <>
              {/* Chat Header */}
              <CardHeader className="border-b border-gray-700/50 pb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-medium">
                      {(selectedTicket.telegram_first_name?.[0] || selectedTicket.telegram_username?.[0] || 'U').toUpperCase()}
                    </div>
                    <div>
                      <p className="font-medium text-white">{getUserDisplayName(selectedTicket)}</p>
                      <div className="flex items-center gap-2 text-sm">
                        {selectedTicket.telegram_username && (
                          <span className="text-gray-400">@{selectedTicket.telegram_username}</span>
                        )}
                        <span className="text-gray-500">•</span>
                        <span className={`flex items-center gap-1 ${statusConfig[selectedTicket.status]?.textColor}`}>
                          <span className={`w-2 h-2 rounded-full ${statusConfig[selectedTicket.status]?.color}`} />
                          {statusConfig[selectedTicket.status]?.label}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {!selectedTicket.assigned_admin_id && (
                      <Button
                        size="sm"
                        onClick={assignToMe}
                        className="bg-purple-600 hover:bg-purple-700"
                      >
                        Взять в работу
                      </Button>
                    )}
                    
                    {selectedTicket.status !== 'resolved' && selectedTicket.status !== 'closed' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => updateTicketStatus('resolved')}
                        className="border-green-600 text-green-400 hover:bg-green-600/20"
                      >
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Решено
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              
              {/* Messages */}
              <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
                {selectedTicket.messages?.map(message => (
                  <div
                    key={message.id}
                    className={`flex ${message.sender_type === 'admin' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[70%] rounded-2xl px-4 py-2 ${
                        message.sender_type === 'admin'
                          ? 'bg-purple-600 text-white rounded-br-none'
                          : 'bg-gray-700 text-white rounded-bl-none'
                      }`}
                    >
                      {message.sender_type === 'admin' && message.sender_admin_name && (
                        <p className="text-xs text-purple-200 mb-1">{message.sender_admin_name}</p>
                      )}
                      <p className="text-sm whitespace-pre-wrap">{message.text}</p>
                      <p className={`text-xs mt-1 ${
                        message.sender_type === 'admin' ? 'text-purple-200' : 'text-gray-400'
                      }`}>
                        {formatMessageTime(message.created_at)}
                        {message.sender_type === 'admin' && message.delivered_at && (
                          <span className="ml-1">✓✓</span>
                        )}
                      </p>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </CardContent>
              
              {/* Message Input */}
              <div className="p-4 border-t border-gray-700/50">
                <div className="flex gap-2">
                  <Input
                    placeholder="Введите сообщение..."
                    value={messageText}
                    onChange={(e) => setMessageText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                    className="flex-1 bg-gray-900/50 border-gray-600"
                    disabled={sendingMessage}
                  />
                  <Button
                    onClick={sendMessage}
                    disabled={!messageText.trim() || sendingMessage}
                    className="bg-purple-600 hover:bg-purple-700"
                  >
                    {sendingMessage ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Ответ будет отправлен пользователю в Telegram
                </p>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <MessageCircle className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>Выберите обращение для просмотра</p>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
