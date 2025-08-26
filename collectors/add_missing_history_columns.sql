-- 이력 관리를 위해 누락된 컬럼만 추가

BEGIN;

-- 1. 누락된 컬럼 추가 (is_active, last_seen_date는 이미 존재)
ALTER TABLE public.properties 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS deletion_reason TEXT;

-- 2. 인덱스 추가 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_properties_deleted_at ON public.properties(deleted_at);

-- 3. 변경사항 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'properties' 
    AND column_name IN ('is_active', 'deleted_at', 'deletion_reason', 'last_seen_date')
ORDER BY column_name;

COMMIT;