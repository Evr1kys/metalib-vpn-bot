'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { FiSend, FiUsers, FiImage, FiLink, FiPlus, FiTrash2, FiCheckCircle, FiAlertCircle, FiClock, FiEye } from 'react-icons/fi'
import toast from 'react-hot-toast'

export default function BroadcastPage() {
  const [message, setMessage] = useState('')
  const [target, setTarget] = useState('all')
  const [photoUrl, setPhotoUrl] = useState('')
  const [buttons, setButtons] = useState<{ text: string; url: string }[]>([])
  const [showPreview, setShowPreview] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const queryClient = useQueryClient()

  const { data: history, refetch: refetchHistory } = useQuery({
    queryKey: ['broadcast-history'],
    queryFn: () => apiClient.get('/broadcast/logs')
  })

  const sendMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/broadcast', data),
    onSuccess: (result) => {
      toast.success(`Отправлено: ${result.sent || 0} сообщений`)
      setMessage('')
      setPhotoUrl('')
      setButtons([])
      refetchHistory()
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Ошибка отправки'),
  })

  const deleteMutation = useMutation({
    mutationFn: (broadcastId: string) => apiClient.delete(`/broadcast/logs/${broadcastId}`),
    onSuccess: (result) => {
      toast.success(result.message || 'Рассылка удалена')
      refetchHistory()
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Ошибка удаления'),
  })

  const previewMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/broadcast', { ...data, preview: true }),
    onSuccess: (result) => {
      toast.success(`Будет отправлено ${result.target_users} пользователям`)
    },
  })

  const addButton = () => {
    if (buttons.length < 3) {
      setButtons([...buttons, { text: '', url: '' }])
    }
  }

  const removeButton = (index: number) => {
    setButtons(buttons.filter((_, i) => i !== index))
  }

  const updateButton = (index: number, field: 'text' | 'url', value: string) => {
    const newButtons = [...buttons]
    newButtons[index][field] = value
    setButtons(newButtons)
  }

  const handleSend = () => {
    if (!message.trim()) {
      toast.error('Введите сообщение')
      return
    }

    const validButtons = buttons.filter(b => b.text && b.url)

    sendMutation.mutate({
      message,
      target,
      photo_url: photoUrl || undefined,
      buttons: validButtons.length > 0 ? validButtons : undefined,
    })
  }

  const handlePreview = () => {
    if (!message.trim()) {
      toast.error('Введите сообщение')
      return
    }

    previewMutation.mutate({
      message,
      target,
      photo_url: photoUrl || undefined,
    })
  }

  const historyList = Array.isArray(history) ? history : []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gradient-text">Рассылка</h1>
          <p className="mt-2 text-gray-400">Отправка сообщений пользователям</p>
        </div>
        <button 
          onClick={() => setShowHistory(!showHistory)}
          className={`px-4 py-2 rounded-xl border transition-colors ${
            showHistory 
              ? 'bg-purple-500/20 border-purple-500 text-purple-400' 
              : 'bg-[#1a1a2e] border-purple-500/20 text-gray-300 hover:text-white'
          }`}
        >
          <FiClock className="inline mr-2" />
          История
        </button>
      </div>

      {showHistory ? (
        /* History View */
        <div className="dark-card p-6">
          <h2 className="text-xl font-bold text-white mb-4">История рассылок</h2>
          {historyList.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FiSend className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Рассылок пока не было</p>
            </div>
          ) : (
            <div className="space-y-3">
              {historyList.map((item: any) => (
                <div key={item.id} className="p-4 rounded-xl bg-[#1a1a2e] border border-purple-500/10">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      {item.has_photo && <FiImage className="text-purple-400" />}
                      {item.has_buttons && <FiLink className="text-blue-400" />}
                      <span className="text-gray-400 text-sm">{item.target}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-gray-500">
                        {new Date(item.created_at).toLocaleString('ru-RU')}
                      </span>
                      <button
                        onClick={() => {
                          if (confirm('Удалить рассылку? Сообщения будут удалены у всех пользователей.')) {
                            deleteMutation.mutate(item.id)
                          }
                        }}
                        disabled={deleteMutation.isPending}
                        className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                        title="Удалить рассылку"
                      >
                        <FiTrash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  <p className="text-white mb-2 line-clamp-2">{item.message}</p>
                  <div className="flex items-center space-x-4 text-sm">
                    <span className="text-green-400">
                      <FiCheckCircle className="inline mr-1" />
                      {item.sent_count} отправлено
                    </span>
                    {item.failed_count > 0 && (
                      <span className="text-red-400">
                        <FiAlertCircle className="inline mr-1" />
                        {item.failed_count} ошибок
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* Compose View */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Compose Form */}
          <div className="dark-card p-6">
            <h2 className="text-xl font-bold text-white mb-4">Новая рассылка</h2>
            
            <div className="space-y-4">
              {/* Target */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Получатели</label>
                <select
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="all">Все пользователи</option>
                  <option value="active">С активной подпиской</option>
                  <option value="inactive">Без подписки</option>
                </select>
              </div>

              {/* Message */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Сообщение</label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={6}
                  placeholder="Введите текст рассылки...&#10;&#10;Поддерживается HTML: <b>жирный</b>, <i>курсив</i>, <code>код</code>"
                  className="w-full px-4 py-3 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                />
              </div>

              {/* Photo URL */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  <FiImage className="inline mr-2" />
                  Фото (URL)
                </label>
                <input
                  type="url"
                  value={photoUrl}
                  onChange={(e) => setPhotoUrl(e.target.value)}
                  placeholder="https://example.com/image.jpg"
                  className="w-full h-11 px-4 bg-[#1a1a2e] border border-purple-500/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              {/* Buttons */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-gray-300">
                    <FiLink className="inline mr-2" />
                    Кнопки (макс. 3)
                  </label>
                  {buttons.length < 3 && (
                    <button
                      onClick={addButton}
                      className="text-purple-400 hover:text-purple-300 text-sm flex items-center"
                    >
                      <FiPlus className="mr-1" /> Добавить
                    </button>
                  )}
                </div>
                
                <div className="space-y-2">
                  {buttons.map((button, index) => (
                    <div key={index} className="flex space-x-2">
                      <input
                        type="text"
                        value={button.text}
                        onChange={(e) => updateButton(index, 'text', e.target.value)}
                        placeholder="Текст кнопки"
                        className="flex-1 h-10 px-3 bg-[#1a1a2e] border border-purple-500/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                      <input
                        type="url"
                        value={button.url}
                        onChange={(e) => updateButton(index, 'url', e.target.value)}
                        placeholder="https://..."
                        className="flex-1 h-10 px-3 bg-[#1a1a2e] border border-purple-500/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                      <button
                        onClick={() => removeButton(index)}
                        className="p-2 text-red-400 hover:text-red-300"
                      >
                        <FiTrash2 />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex space-x-3 pt-4">
                <button
                  onClick={handlePreview}
                  disabled={previewMutation.isPending}
                  className="flex-1 px-4 py-3 rounded-xl bg-[#1a1a2e] border border-purple-500/20 text-gray-300 hover:text-white flex items-center justify-center transition-colors"
                >
                  <FiEye className="mr-2" />
                  Превью
                </button>
                <button
                  onClick={handleSend}
                  disabled={sendMutation.isPending || !message.trim()}
                  className="flex-1 btn-gradient py-3 rounded-xl flex items-center justify-center disabled:opacity-50"
                >
                  {sendMutation.isPending ? (
                    <span>Отправка...</span>
                  ) : (
                    <>
                      <FiSend className="mr-2" />
                      Отправить
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Preview */}
          <div className="dark-card p-6">
            <h2 className="text-xl font-bold text-white mb-4">Предпросмотр</h2>
            
            <div className="bg-[#1a1a2e] rounded-xl p-4 min-h-[300px]">
              {/* Telegram-style message preview */}
              <div className="max-w-sm mx-auto">
                {photoUrl && (
                  <div className="mb-3 rounded-lg overflow-hidden bg-gray-800">
                    <img 
                      src={photoUrl} 
                      alt="Preview" 
                      className="w-full h-40 object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="%23333" width="100%" height="100%"/><text fill="%23666" x="50%" y="50%" text-anchor="middle" dy=".3em">Фото</text></svg>'
                      }}
                    />
                  </div>
                )}
                
                <div className="bg-[#2b5278] rounded-lg p-3 text-white text-sm whitespace-pre-wrap">
                  {message || <span className="text-gray-400 italic">Введите сообщение...</span>}
                </div>
                
                {buttons.filter(b => b.text).length > 0 && (
                  <div className="mt-2 space-y-1">
                    {buttons.filter(b => b.text).map((button, index) => (
                      <div 
                        key={index}
                        className="w-full py-2 px-4 bg-[#3a3a5c] rounded-lg text-center text-blue-400 text-sm"
                      >
                        {button.text}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Target info */}
            <div className="mt-4 p-3 rounded-lg bg-[#1a1a2e] border border-purple-500/20">
              <div className="flex items-center text-gray-400 text-sm">
                <FiUsers className="mr-2" />
                Получатели: {
                  target === 'all' ? 'Все пользователи' :
                  target === 'active' ? 'С активной подпиской' :
                  'Без подписки'
                }
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
