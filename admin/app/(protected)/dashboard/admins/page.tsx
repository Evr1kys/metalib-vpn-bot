'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';
import {
  FiUserPlus,
  FiEdit2,
  FiTrash2,
  FiShield,
  FiLock,
  FiUnlock,
  FiRefreshCw,
  FiCheck,
  FiX,
  FiChevronDown,
  FiChevronUp,
  FiMail,
  FiMessageSquare,
  FiUser,
  FiCopy,
} from 'react-icons/fi';

interface Permission {
  key: string;
  label: string;
}

interface Admin {
  id: string;
  username: string;
  email?: string;
  telegram_id?: number;
  first_name?: string;
  last_name?: string;
  role: 'owner' | 'admin' | 'moderator' | 'support' | 'viewer';
  is_active: boolean;
  permissions: string[];
  custom_permissions?: string[];
  description?: string;
  avatar_url?: string;
  created_at: string;
  last_login_at?: string;
  last_login_ip?: string;
}

interface RoleInfo {
  value: string;
  label: string;
}

const roleConfig: Record<string, { label: string; color: string; bg: string; text: string; border: string }> = {
  owner: { label: 'Владелец', color: 'from-purple-500 to-pink-500', bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/30' },
  admin: { label: 'Администратор', color: 'from-blue-500 to-cyan-500', bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
  moderator: { label: 'Модератор', color: 'from-green-500 to-emerald-500', bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
  support: { label: 'Поддержка', color: 'from-yellow-500 to-orange-500', bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30' },
  viewer: { label: 'Только просмотр', color: 'from-gray-500 to-slate-500', bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30' },
};

const permissionGroups: Record<string, string[]> = {
  'Дашборд': ['view_dashboard', 'view_analytics'],
  'Пользователи': ['view_users', 'edit_users', 'delete_users', 'ban_users'],
  'Подписки': ['view_subscriptions', 'edit_subscriptions', 'create_subscriptions', 'cancel_subscriptions'],
  'Платежи': ['view_payments', 'refund_payments'],
  'Серверы и VPN': ['view_servers', 'manage_servers', 'view_vpn_accounts', 'manage_vpn_accounts'],
  'Тарифы и промо': ['view_plans', 'manage_plans', 'view_promo_codes', 'manage_promo_codes'],
  'Уведомления': ['send_notifications', 'send_broadcasts'],
  'Поддержка': ['view_support_tickets', 'respond_support', 'view_telegram_messages', 'respond_telegram'],
  'Администрирование': ['view_admins', 'manage_admins', 'view_audit_logs', 'view_system_logs', 'view_settings', 'manage_settings'],
};

export default function AdminsPage() {
  const [admins, setAdmins] = useState<Admin[]>([]);
  const [allPermissions, setAllPermissions] = useState<Permission[]>([]);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [defaultPermissions, setDefaultPermissions] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingAdmin, setEditingAdmin] = useState<Admin | null>(null);
  const [expandedAdmin, setExpandedAdmin] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    telegram_id: '',
    role: 'support' as string,
    first_name: '',
    last_name: '',
    description: '',
    custom_permissions: [] as string[],
    useCustomPermissions: false,
  });

  useEffect(() => {
    fetchAdmins();
    fetchPermissions();
  }, []);

  const fetchAdmins = async () => {
    try {
      setLoading(true);
      const response = await api.get('/admin/list');
      setAdmins(response || []);
    } catch (error) {
      console.error('Error fetching admins:', error);
      toast.error('Ошибка загрузки администраторов');
    } finally {
      setLoading(false);
    }
  };

  const fetchPermissions = async () => {
    try {
      const response = await api.get('/admin/permissions');
      setAllPermissions(response.permissions || []);
      setRoles(response.roles || []);
      setDefaultPermissions(response.default_permissions || {});
    } catch (error) {
      console.error('Error fetching permissions:', error);
    }
  };

  const handleCreateAdmin = async () => {
    if (!formData.username || !formData.password) {
      toast.error('Заполните обязательные поля');
      return;
    }

    try {
      await api.post('/admin/create', {
        username: formData.username,
        email: formData.email || null,
        password: formData.password,
        telegram_id: formData.telegram_id ? Number(formData.telegram_id) : null,
        role: formData.role,
        first_name: formData.first_name || null,
        last_name: formData.last_name || null,
        description: formData.description || null,
        custom_permissions: formData.useCustomPermissions ? formData.custom_permissions : null,
      });
      toast.success('Администратор создан');
      setShowModal(false);
      resetForm();
      fetchAdmins();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Ошибка создания');
    }
  };

  const handleUpdateAdmin = async () => {
    if (!editingAdmin) return;

    try {
      await api.put(`/admin/${editingAdmin.id}`, {
        role: formData.role,
        first_name: formData.first_name || null,
        last_name: formData.last_name || null,
        email: formData.email || null,
        telegram_id: formData.telegram_id ? Number(formData.telegram_id) : null,
        description: formData.description || null,
        custom_permissions: formData.useCustomPermissions ? formData.custom_permissions : null,
        password: formData.password || undefined,
      });
      toast.success('Администратор обновлен');
      setShowModal(false);
      setEditingAdmin(null);
      resetForm();
      fetchAdmins();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Ошибка обновления');
    }
  };

  const handleDeleteAdmin = async (id: string) => {
    if (!confirm('Вы уверены, что хотите удалить этого администратора?')) return;

    try {
      await api.delete(`/admin/${id}`);
      toast.success('Администратор удален');
      fetchAdmins();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Ошибка удаления');
    }
  };

  const handleToggleActive = async (admin: Admin) => {
    try {
      await api.put(`/admin/${admin.id}`, {
        is_active: !admin.is_active,
      });
      toast.success(admin.is_active ? 'Администратор заблокирован' : 'Администратор разблокирован');
      fetchAdmins();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Ошибка изменения статуса');
    }
  };

  const resetForm = () => {
    setFormData({
      username: '',
      email: '',
      password: '',
      telegram_id: '',
      role: 'support',
      first_name: '',
      last_name: '',
      description: '',
      custom_permissions: [],
      useCustomPermissions: false,
    });
  };

  const openCreateModal = () => {
    setEditingAdmin(null);
    resetForm();
    setShowModal(true);
  };

  const openEditModal = (admin: Admin) => {
    setEditingAdmin(admin);
    setFormData({
      username: admin.username,
      email: admin.email || '',
      password: '',
      telegram_id: admin.telegram_id?.toString() || '',
      role: admin.role,
      first_name: admin.first_name || '',
      last_name: admin.last_name || '',
      description: admin.description || '',
      custom_permissions: admin.custom_permissions || admin.permissions || [],
      useCustomPermissions: !!admin.custom_permissions,
    });
    setShowModal(true);
  };

  const togglePermission = (perm: string) => {
    setFormData(prev => ({
      ...prev,
      custom_permissions: prev.custom_permissions.includes(perm)
        ? prev.custom_permissions.filter(p => p !== perm)
        : [...prev.custom_permissions, perm]
    }));
  };

  const getPermissionLabel = (key: string) => {
    const perm = allPermissions.find(p => p.key === key);
    return perm?.label || key;
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Скопировано');
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            Администраторы
          </h1>
          <p className="text-white/60 mt-1">
            Управление доступом и правами в панели
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchAdmins}
            className="flex items-center gap-2 px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all text-white/80"
          >
            <FiRefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            Обновить
          </button>
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl hover:opacity-90 transition-all shadow-lg shadow-purple-500/25"
          >
            <FiUserPlus size={18} />
            Добавить админа
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        {Object.entries(roleConfig).map(([role, config]) => {
          const count = admins.filter(a => a.role === role).length;
          return (
            <div
              key={role}
              className={`p-4 rounded-xl bg-gradient-to-br ${config.bg} border ${config.border} backdrop-blur-sm`}
            >
              <div className={`text-2xl font-bold ${config.text}`}>{count}</div>
              <div className="text-white/60 text-sm">{config.label}</div>
            </div>
          );
        })}
      </div>

      {/* Admins List */}
      <div className="space-y-4">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <FiRefreshCw className="w-8 h-8 animate-spin text-purple-400" />
          </div>
        ) : admins.length === 0 ? (
          <div className="text-center py-20 text-white/40">
            <FiShield className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <p>Администраторы не найдены</p>
          </div>
        ) : (
          admins.map((admin) => {
            const config = roleConfig[admin.role] || roleConfig.viewer;
            const isExpanded = expandedAdmin === admin.id;
            
            return (
              <div
                key={admin.id}
                className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl overflow-hidden hover:border-white/20 transition-all"
              >
                {/* Main Row */}
                <div className="p-5 flex items-center gap-5">
                  {/* Avatar */}
                  <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${config.color} flex items-center justify-center text-white font-bold text-xl shadow-lg`}>
                    {admin.first_name?.[0] || admin.username[0].toUpperCase()}
                  </div>
                  
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-semibold text-white truncate">
                        {admin.first_name && admin.last_name 
                          ? `${admin.first_name} ${admin.last_name}`
                          : admin.username}
                      </h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text} border ${config.border}`}>
                        {config.label}
                      </span>
                      {!admin.is_active && (
                        <span className="px-3 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">
                          Заблокирован
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-sm text-white/50">
                      <span className="flex items-center gap-1">
                        <FiUser size={14} />
                        @{admin.username}
                      </span>
                      {admin.email && (
                        <span className="flex items-center gap-1">
                          <FiMail size={14} />
                          {admin.email}
                        </span>
                      )}
                      {admin.telegram_id && (
                        <span className="flex items-center gap-1">
                          <FiMessageSquare size={14} />
                          TG: {admin.telegram_id}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {/* Last Login */}
                  <div className="text-right text-sm">
                    <div className="text-white/40">Последний вход</div>
                    <div className="text-white/70">
                      {admin.last_login_at
                        ? new Date(admin.last_login_at).toLocaleString('ru-RU', {
                            day: '2-digit',
                            month: 'short',
                            hour: '2-digit',
                            minute: '2-digit'
                          })
                        : 'Никогда'}
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setExpandedAdmin(isExpanded ? null : admin.id)}
                      className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-all"
                      title="Подробнее"
                    >
                      {isExpanded ? <FiChevronUp size={18} /> : <FiChevronDown size={18} />}
                    </button>
                    <button
                      onClick={() => openEditModal(admin)}
                      className="p-2.5 rounded-xl bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 transition-all"
                      title="Редактировать"
                    >
                      <FiEdit2 size={18} />
                    </button>
                    <button
                      onClick={() => handleToggleActive(admin)}
                      className={`p-2.5 rounded-xl transition-all ${
                        admin.is_active
                          ? 'bg-orange-500/20 hover:bg-orange-500/30 text-orange-400'
                          : 'bg-green-500/20 hover:bg-green-500/30 text-green-400'
                      }`}
                      title={admin.is_active ? 'Заблокировать' : 'Разблокировать'}
                    >
                      {admin.is_active ? <FiLock size={18} /> : <FiUnlock size={18} />}
                    </button>
                    {admin.role !== 'owner' && (
                      <button
                        onClick={() => handleDeleteAdmin(admin.id)}
                        className="p-2.5 rounded-xl bg-red-500/20 hover:bg-red-500/30 text-red-400 transition-all"
                        title="Удалить"
                      >
                        <FiTrash2 size={18} />
                      </button>
                    )}
                  </div>
                </div>
                
                {/* Expanded Details */}
                {isExpanded && (
                  <div className="px-5 pb-5 border-t border-white/10 pt-4">
                    <div className="grid grid-cols-3 gap-6">
                      {/* Info Column */}
                      <div className="space-y-3">
                        <h4 className="text-sm font-medium text-white/40 uppercase tracking-wider">Информация</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-white/50">ID:</span>
                            <span className="text-white/80 font-mono flex items-center gap-1">
                              {admin.id.slice(0, 8)}...
                              <button onClick={() => copyToClipboard(admin.id)} className="text-white/40 hover:text-white/60">
                                <FiCopy size={12} />
                              </button>
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-white/50">Создан:</span>
                            <span className="text-white/80">
                              {new Date(admin.created_at).toLocaleDateString('ru-RU')}
                            </span>
                          </div>
                          {admin.last_login_ip && (
                            <div className="flex justify-between">
                              <span className="text-white/50">IP:</span>
                              <span className="text-white/80 font-mono">{admin.last_login_ip}</span>
                            </div>
                          )}
                          {admin.description && (
                            <div className="pt-2">
                              <span className="text-white/50">Описание:</span>
                              <p className="text-white/70 mt-1">{admin.description}</p>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* Permissions Column */}
                      <div className="col-span-2 space-y-3">
                        <h4 className="text-sm font-medium text-white/40 uppercase tracking-wider">
                          Права доступа ({admin.permissions?.length || 0})
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {(admin.permissions || []).slice(0, 12).map(perm => (
                            <span
                              key={perm}
                              className="px-2.5 py-1 rounded-lg bg-white/5 text-white/60 text-xs border border-white/10"
                            >
                              {getPermissionLabel(perm)}
                            </span>
                          ))}
                          {(admin.permissions?.length || 0) > 12 && (
                            <span className="px-2.5 py-1 rounded-lg bg-purple-500/20 text-purple-400 text-xs border border-purple-500/30">
                              +{admin.permissions.length - 12} ещё
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#1a1a2e] border border-white/10 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden shadow-2xl">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">
                {editingAdmin ? 'Редактировать администратора' : 'Создать администратора'}
              </h2>
              <button
                onClick={() => { setShowModal(false); setEditingAdmin(null); }}
                className="p-2 rounded-lg hover:bg-white/10 text-white/60 hover:text-white transition-all"
              >
                <FiX size={20} />
              </button>
            </div>
            
            {/* Modal Body */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)] space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                {!editingAdmin && (
                  <div>
                    <label className="block text-sm font-medium text-white/60 mb-2">
                      Имя пользователя *
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                      className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all"
                      placeholder="admin_username"
                    />
                  </div>
                )}
                
                <div>
                  <label className="block text-sm font-medium text-white/60 mb-2">
                    Роль *
                  </label>
                  <select
                    value={formData.role}
                    onChange={(e) => {
                      const newRole = e.target.value;
                      setFormData({ 
                        ...formData, 
                        role: newRole,
                        custom_permissions: defaultPermissions[newRole] || []
                      });
                    }}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all"
                  >
                    {roles.map(role => (
                      <option key={role.value} value={role.value} className="bg-[#1a1a2e]">
                        {role.label}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-white/60 mb-2">
                    Имя
                  </label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all"
                    placeholder="Иван"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-white/60 mb-2">
                    Фамилия
                  </label>
                  <input
                    type="text"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all"
                    placeholder="Петров"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-white/60 mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all"
                    placeholder="admin@example.com"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-white/60 mb-2">
                    Telegram ID
                  </label>
                  <input
                    type="text"
                    value={formData.telegram_id}
                    onChange={(e) => setFormData({ ...formData, telegram_id: e.target.value })}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all"
                    placeholder="123456789"
                  />
                </div>
                
                <div className={editingAdmin ? 'col-span-2' : ''}>
                  <label className="block text-sm font-medium text-white/60 mb-2">
                    {editingAdmin ? 'Новый пароль (оставьте пустым, чтобы не менять)' : 'Пароль *'}
                  </label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all"
                    placeholder="••••••••"
                  />
                </div>
              </div>
              
              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-white/60 mb-2">
                  Описание / Заметки
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={2}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all resize-none"
                  placeholder="Дополнительная информация об администраторе..."
                />
              </div>
              
              {/* Custom Permissions Toggle */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setFormData(prev => ({ ...prev, useCustomPermissions: !prev.useCustomPermissions }))}
                  className={`w-12 h-6 rounded-full transition-all relative ${
                    formData.useCustomPermissions ? 'bg-purple-500' : 'bg-white/20'
                  }`}
                >
                  <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${
                    formData.useCustomPermissions ? 'left-7' : 'left-1'
                  }`} />
                </button>
                <span className="text-white/70">Настроить права вручную</span>
              </div>
              
              {/* Permissions Grid */}
              {formData.useCustomPermissions && (
                <div className="space-y-4 p-4 bg-white/5 rounded-xl border border-white/10">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-medium text-white/60 uppercase tracking-wider">Права доступа</h4>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, custom_permissions: allPermissions.map(p => p.key) }))}
                        className="text-xs text-purple-400 hover:text-purple-300"
                      >
                        Выбрать все
                      </button>
                      <span className="text-white/20">|</span>
                      <button
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, custom_permissions: [] }))}
                        className="text-xs text-white/40 hover:text-white/60"
                      >
                        Снять все
                      </button>
                    </div>
                  </div>
                  
                  {Object.entries(permissionGroups).map(([group, perms]) => (
                    <div key={group} className="space-y-2">
                      <h5 className="text-sm font-medium text-white/50">{group}</h5>
                      <div className="grid grid-cols-2 gap-2">
                        {perms.map(perm => (
                          <label
                            key={perm}
                            className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-all ${
                              formData.custom_permissions.includes(perm)
                                ? 'bg-purple-500/20 border border-purple-500/30'
                                : 'bg-white/5 border border-white/10 hover:bg-white/10'
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={formData.custom_permissions.includes(perm)}
                              onChange={() => togglePermission(perm)}
                              className="sr-only"
                            />
                            <span className={`w-4 h-4 rounded flex items-center justify-center ${
                              formData.custom_permissions.includes(perm)
                                ? 'bg-purple-500 text-white'
                                : 'bg-white/10'
                            }`}>
                              {formData.custom_permissions.includes(perm) && <FiCheck size={12} />}
                            </span>
                            <span className="text-sm text-white/70">{getPermissionLabel(perm)}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-white/10 flex gap-3">
              <button
                onClick={() => { setShowModal(false); setEditingAdmin(null); }}
                className="flex-1 px-4 py-3 bg-white/5 border border-white/10 text-white rounded-xl hover:bg-white/10 transition-all"
              >
                Отмена
              </button>
              <button
                onClick={editingAdmin ? handleUpdateAdmin : handleCreateAdmin}
                className="flex-1 px-4 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl hover:opacity-90 transition-all shadow-lg"
              >
                {editingAdmin ? 'Сохранить' : 'Создать'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
