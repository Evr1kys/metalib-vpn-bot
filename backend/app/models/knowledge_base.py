"""
Knowledge Base & Blog models - FAQ, статьи, гайды
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.models.base import Base, UUIDMixin, TimestampMixin


class ArticleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ArticleCategory(str, Enum):
    FAQ = "faq"                 # Часто задаваемые вопросы
    GUIDE = "guide"             # Гайды по настройке
    NEWS = "news"               # Новости
    RKN = "rkn"                 # Новости про РКН и блокировки
    TIPS = "tips"               # Советы и лайфхаки
    SECURITY = "security"       # Безопасность
    COMPARISON = "comparison"   # Сравнения протоколов и т.д.


class KnowledgeBaseArticle(Base, UUIDMixin, TimestampMixin):
    """Статья в базе знаний / блоге"""
    __tablename__ = "kb_articles"
    
    # Заголовки
    title = Column(String(255), nullable=False)
    title_en = Column(String(255), nullable=True)
    
    # URL slug для SEO
    slug = Column(String(255), nullable=False, unique=True, index=True)
    
    # Контент (HTML или Markdown)
    content = Column(Text, nullable=False)
    content_en = Column(Text, nullable=True)
    
    # Краткое описание для превью
    excerpt = Column(Text, nullable=True)
    excerpt_en = Column(Text, nullable=True)
    
    # Категория
    category = Column(SQLEnum(ArticleCategory), default=ArticleCategory.FAQ)
    
    # Теги для поиска
    tags = Column(JSON, nullable=True)  # ["vpn", "youtube", "обход блокировок"]
    
    # SEO
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    meta_keywords = Column(String(500), nullable=True)
    
    # Изображения
    featured_image = Column(String(500), nullable=True)
    og_image = Column(String(500), nullable=True)
    
    # Автор
    author_id = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)
    
    # Статус
    status = Column(SQLEnum(ArticleStatus), default=ArticleStatus.DRAFT)
    
    # Публикация
    published_at = Column(DateTime, nullable=True)
    
    # Статистика
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    
    # Порядок (для FAQ)
    sort_order = Column(Integer, default=0)
    
    # Избранное (показывать на главной)
    is_featured = Column(Boolean, default=False)
    
    # Для FAQ - показывать в боте
    show_in_bot = Column(Boolean, default=False)


class FAQCategory(Base, UUIDMixin, TimestampMixin):
    """Категории FAQ"""
    __tablename__ = "faq_categories"
    
    name = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=True)
    
    slug = Column(String(100), nullable=False, unique=True)
    
    description = Column(Text, nullable=True)
    description_en = Column(Text, nullable=True)
    
    icon = Column(String(50), nullable=True)  # emoji или icon name
    
    sort_order = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    
    # Связь со статьями через JSON tags


class ArticleView(Base, UUIDMixin, TimestampMixin):
    """Просмотры статей"""
    __tablename__ = "article_views"
    
    article_id = Column(UUID(as_uuid=True), ForeignKey("kb_articles.id"), nullable=False)
    article = relationship("KnowledgeBaseArticle", backref="views")
    
    # Пользователь (опционально)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # IP для анонимных
    ip_address = Column(String(45), nullable=True)
    
    # User agent
    user_agent = Column(String(500), nullable=True)
    
    # Откуда пришёл
    referrer = Column(String(500), nullable=True)


class ArticleLike(Base, UUIDMixin, TimestampMixin):
    """Лайки статей"""
    __tablename__ = "article_likes"
    
    article_id = Column(UUID(as_uuid=True), ForeignKey("kb_articles.id"), nullable=False)
    article = relationship("KnowledgeBaseArticle", backref="likes")
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    is_helpful = Column(Boolean, default=True)  # True = полезно, False = не полезно
