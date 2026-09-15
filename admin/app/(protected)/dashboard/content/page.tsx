'use client'

import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { FiUpload, FiImage, FiSave } from 'react-icons/fi'
import toast from 'react-hot-toast'

export default function ContentPage() {
  const [activeTab, setActiveTab] = useState<'texts' | 'images'>('texts')

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Контент и медиа</h1>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-6">
        <button
          onClick={() => setActiveTab('texts')}
          className={`px-6 py-3 font-medium transition ${
            activeTab === 'texts'
              ? 'border-b-2 border-primary-600 text-primary-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Тексты сообщений
        </button>
        <button
          onClick={() => setActiveTab('images')}
          className={`px-6 py-3 font-medium transition ${
            activeTab === 'images'
              ? 'border-b-2 border-primary-600 text-primary-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Изображения
        </button>
      </div>

      {activeTab === 'texts' ? <TextsTab /> : <ImagesTab />}
    </div>
  )
}

function TextsTab() {
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => apiClient.getSettings()
  })
  const [formData, setFormData] = useState({
    welcome_message: '',
    help_message: '',
    subscription_info: '',
    payment_instructions: '',
  })

  // @ts-ignore
  const mutation = useMutation({
    mutationFn: (data: any) => apiClient.updateSettings(data),
    onSuccess: () => toast.success('Тексты обновлены'),
    onError: () => toast.error('Ошибка'),
  })

  useState(() => {
    if (settings) {
      setFormData({
        welcome_message: settings.welcome_message || '',
        help_message: settings.help_message || '',
        subscription_info: settings.subscription_info || '',
        payment_instructions: settings.payment_instructions || '',
      })
    }
  })

  if (isLoading) {
    return <div className="text-center py-8">Загрузка...</div>
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm p-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Приветственное сообщение
        </label>
        <textarea
          value={formData.welcome_message}
          onChange={(e) => setFormData({ ...formData, welcome_message: e.target.value })}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          rows={4}
          placeholder="Привет! 👋 Добро пожаловать в MetaLib VPN..."
        />
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Справочное сообщение
        </label>
        <textarea
          value={formData.help_message}
          onChange={(e) => setFormData({ ...formData, help_message: e.target.value })}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          rows={6}
          placeholder="❓ Помощь..."
        />
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Информация о подписке
        </label>
        <textarea
          value={formData.subscription_info}
          onChange={(e) => setFormData({ ...formData, subscription_info: e.target.value })}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          rows={4}
          placeholder="Ваша подписка активна до..."
        />
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Инструкции по оплате
        </label>
        <textarea
          value={formData.payment_instructions}
          onChange={(e) => setFormData({ ...formData, payment_instructions: e.target.value })}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          rows={4}
          placeholder="Для оплаты нажмите кнопку ниже..."
        />
      </div>

      <button
        onClick={() => mutation.mutate(formData)}
        disabled={mutation.isLoading}
        className="flex items-center px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition"
      >
        <FiSave className="mr-2" size={20} />
        {mutation.isLoading ? 'Сохранение...' : 'Сохранить изменения'}
      </button>
    </div>
  )
}

function ImagesTab() {
  const [uploadType, setUploadType] = useState<'banner' | 'logo'>('banner')
  const [preview, setPreview] = useState<string | null>(null)

  // @ts-ignore
  const uploadMutation = useMutation({
    mutationFn: (file: File) => apiClient.uploadImage(file, uploadType),
    onSuccess: () => {
      toast.success('Изображение загружено')
      setPreview(null)
    },
    onError: () => toast.error('Ошибка загрузки'),
  })

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onloadend = () => {
        setPreview(reader.result as string)
      }
      reader.readAsDataURL(file)
      uploadMutation.mutate(file)
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Загрузить изображение</h2>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Тип изображения
          </label>
          <select
            value={uploadType}
            onChange={(e) => setUploadType(e.target.value as 'banner' | 'logo')}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          >
            <option value="banner">Баннер (для приветствия)</option>
            <option value="logo">Логотип</option>
          </select>
        </div>

        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
          <input
            type="file"
            id="file-upload"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />
          <label
            htmlFor="file-upload"
            className="cursor-pointer flex flex-col items-center"
          >
            <FiUpload className="text-gray-400 mb-4" size={48} />
            <span className="text-sm font-medium text-gray-900">
              Нажмите для загрузки
            </span>
            <span className="text-xs text-gray-500 mt-1">
              PNG, JPG до 5MB
            </span>
          </label>
        </div>

        {preview && (
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-700 mb-2">Предпросмотр:</p>
            <img
              src={preview}
              alt="Preview"
              className="max-w-full h-auto rounded-lg border border-gray-200"
            />
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center mb-4">
            <FiImage className="text-primary-600 mr-2" size={20} />
            <h3 className="text-lg font-semibold text-gray-900">Текущий баннер</h3>
          </div>
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <p className="text-sm text-gray-500 text-center">Нет изображения</p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6">
          <div className="flex items-center mb-4">
            <FiImage className="text-primary-600 mr-2" size={20} />
            <h3 className="text-lg font-semibold text-gray-900">Текущий логотип</h3>
          </div>
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <p className="text-sm text-gray-500 text-center">Нет изображения</p>
          </div>
        </div>
      </div>
    </div>
  )
}
