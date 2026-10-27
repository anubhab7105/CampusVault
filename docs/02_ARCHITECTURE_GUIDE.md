
# Architecture Guide

## High-Level Architecture

React
↓

Axios / Socket.IO
↓

Flask API

↓

Business Services

↓

Supabase PostgreSQL
Supabase Storage
Redis
Celery

## Principles

- API First
- Stateless Backend
- JWT Authentication
- Modular Blueprints
- Feature Isolation

## Folder Layout

frontend/
backend/
docs/
docker/
tests/

Every feature owns:
- models
- services
- routes
- validation
- tests
- documentation
