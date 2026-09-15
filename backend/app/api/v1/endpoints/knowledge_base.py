"""
Knowledge Base & FAQ API endpoints
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models import (
    KnowledgeBaseArticle, FAQCategory, ArticleView, ArticleLike,
    ArticleStatus, ArticleCategory
)
from app.api.deps import get_current_admin

router = APIRouter()


# ============== Schemas ==============

class ArticleCreate(BaseModel):
    title: str
    title_en: Optional[str] = None
    slug: str
    content: str
    content_en: Optional[str] = None
    excerpt: Optional[str] = None
    category: str = "faq"
    tags: Optional[List[str]] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    status: str = "draft"
    show_in_bot: bool = False
    is_featured: bool = False


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    is_featured: Optional[bool] = None


class FAQCategoryCreate(BaseModel):
    name: str
    name_en: Optional[str] = None
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None


# ============== Public Endpoints ==============

@router.get("/articles")
async def get_articles(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    featured: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get published articles (public)"""
    stmt = select(KnowledgeBaseArticle).where(
        KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED
    )
    
    if category:
        stmt = stmt.where(KnowledgeBaseArticle.category == ArticleCategory(category))
    
    if featured:
        stmt = stmt.where(KnowledgeBaseArticle.is_featured == True)
    
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                KnowledgeBaseArticle.title.ilike(search_term),
                KnowledgeBaseArticle.content.ilike(search_term)
            )
        )
    
    stmt = stmt.order_by(KnowledgeBaseArticle.sort_order, KnowledgeBaseArticle.published_at.desc())
    stmt = stmt.offset(offset).limit(limit)
    
    result = await db.execute(stmt)
    articles = result.scalars().all()
    
    return {
        "articles": [
            {
                "id": str(a.id),
                "title": a.title,
                "slug": a.slug,
                "excerpt": a.excerpt,
                "category": a.category.value,
                "tags": a.tags or [],
                "featured_image": a.featured_image,
                "views_count": a.views_count,
                "likes_count": a.likes_count,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "is_featured": a.is_featured
            }
            for a in articles
        ]
    }


@router.get("/articles/{slug}")
async def get_article(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get single article by slug (public)"""
    stmt = select(KnowledgeBaseArticle).where(
        and_(
            KnowledgeBaseArticle.slug == slug,
            KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED
        )
    )
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Track view
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    
    view = ArticleView(
        article_id=article.id,
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent", "")[:500],
        referrer=request.headers.get("Referer", "")[:500]
    )
    db.add(view)
    article.views_count += 1
    await db.commit()
    
    return {
        "id": str(article.id),
        "title": article.title,
        "title_en": article.title_en,
        "slug": article.slug,
        "content": article.content,
        "content_en": article.content_en,
        "excerpt": article.excerpt,
        "category": article.category.value,
        "tags": article.tags or [],
        "featured_image": article.featured_image,
        "meta_title": article.meta_title or article.title,
        "meta_description": article.meta_description or article.excerpt,
        "views_count": article.views_count,
        "likes_count": article.likes_count,
        "published_at": article.published_at.isoformat() if article.published_at else None
    }


@router.get("/faq")
async def get_faq(
    db: AsyncSession = Depends(get_db)
):
    """Get FAQ articles grouped by category"""
    stmt = select(KnowledgeBaseArticle).where(
        and_(
            KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED,
            KnowledgeBaseArticle.category == ArticleCategory.FAQ
        )
    ).order_by(KnowledgeBaseArticle.sort_order)
    
    result = await db.execute(stmt)
    articles = result.scalars().all()
    
    # Group by tags (as categories)
    grouped = {}
    for a in articles:
        category = (a.tags[0] if a.tags else "general")
        if category not in grouped:
            grouped[category] = []
        grouped[category].append({
            "id": str(a.id),
            "question": a.title,
            "answer": a.content,
            "slug": a.slug
        })
    
    return {"faq": grouped}


@router.post("/articles/{article_id}/like")
async def like_article(
    article_id: str,
    helpful: bool = True,
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Like/rate an article"""
    article = await db.get(KnowledgeBaseArticle, uuid.UUID(article_id))
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    forwarded = request.headers.get("X-Forwarded-For") if request else None
    client_ip = forwarded.split(",")[0].strip() if forwarded else None
    
    like = ArticleLike(
        article_id=article.id,
        ip_address=client_ip,
        is_helpful=helpful
    )
    db.add(like)
    
    if helpful:
        article.likes_count += 1
    
    await db.commit()
    
    return {"success": True, "likes_count": article.likes_count}


# ============== Bot Endpoints ==============

@router.get("/bot/faq")
async def get_bot_faq(
    db: AsyncSession = Depends(get_db)
):
    """Get FAQ for Telegram bot"""
    stmt = select(KnowledgeBaseArticle).where(
        and_(
            KnowledgeBaseArticle.status == ArticleStatus.PUBLISHED,
            KnowledgeBaseArticle.show_in_bot == True
        )
    ).order_by(KnowledgeBaseArticle.sort_order).limit(20)
    
    result = await db.execute(stmt)
    articles = result.scalars().all()
    
    return {
        "faq": [
            {
                "id": str(a.id),
                "question": a.title,
                "answer": a.content[:1000]  # Limit for Telegram
            }
            for a in articles
        ]
    }


# ============== Admin Endpoints ==============

@router.get("/admin/articles")
async def admin_get_articles(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Get all articles"""
    stmt = select(KnowledgeBaseArticle).order_by(KnowledgeBaseArticle.created_at.desc())
    
    if status:
        stmt = stmt.where(KnowledgeBaseArticle.status == ArticleStatus(status))
    if category:
        stmt = stmt.where(KnowledgeBaseArticle.category == ArticleCategory(category))
    
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    articles = result.scalars().all()
    
    # Count total
    count_stmt = select(func.count(KnowledgeBaseArticle.id))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0
    
    return {
        "articles": [
            {
                "id": str(a.id),
                "title": a.title,
                "slug": a.slug,
                "category": a.category.value,
                "status": a.status.value,
                "views_count": a.views_count,
                "is_featured": a.is_featured,
                "show_in_bot": a.show_in_bot,
                "created_at": a.created_at.isoformat(),
                "published_at": a.published_at.isoformat() if a.published_at else None
            }
            for a in articles
        ],
        "total": total
    }


@router.post("/admin/articles")
async def admin_create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Create article"""
    # Check slug uniqueness
    existing = await db.execute(
        select(KnowledgeBaseArticle).where(KnowledgeBaseArticle.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already exists")
    
    article = KnowledgeBaseArticle(
        title=data.title,
        title_en=data.title_en,
        slug=data.slug,
        content=data.content,
        content_en=data.content_en,
        excerpt=data.excerpt,
        category=ArticleCategory(data.category),
        tags=data.tags,
        meta_title=data.meta_title,
        meta_description=data.meta_description,
        status=ArticleStatus(data.status),
        show_in_bot=data.show_in_bot,
        is_featured=data.is_featured,
        author_id=admin.id
    )
    
    if data.status == "published":
        article.published_at = datetime.utcnow()
    
    db.add(article)
    await db.commit()
    await db.refresh(article)
    
    return {"id": str(article.id), "slug": article.slug}


@router.put("/admin/articles/{article_id}")
async def admin_update_article(
    article_id: str,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Update article"""
    article = await db.get(KnowledgeBaseArticle, uuid.UUID(article_id))
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if data.title is not None:
        article.title = data.title
    if data.content is not None:
        article.content = data.content
    if data.excerpt is not None:
        article.excerpt = data.excerpt
    if data.tags is not None:
        article.tags = data.tags
    if data.is_featured is not None:
        article.is_featured = data.is_featured
    if data.status is not None:
        old_status = article.status
        article.status = ArticleStatus(data.status)
        if old_status != ArticleStatus.PUBLISHED and article.status == ArticleStatus.PUBLISHED:
            article.published_at = datetime.utcnow()
    
    await db.commit()
    
    return {"success": True}


@router.delete("/admin/articles/{article_id}")
async def admin_delete_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Delete article"""
    article = await db.get(KnowledgeBaseArticle, uuid.UUID(article_id))
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    await db.delete(article)
    await db.commit()
    
    return {"success": True}
