-- 매물 이력 관리를 위한 스키마 업데이트
-- properties 테이블에 이력 관리 컬럼 추가

BEGIN;

-- 1. 이력 관리 컬럼 추가
ALTER TABLE public.properties 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS deletion_reason TEXT,
ADD COLUMN IF NOT EXISTS last_seen_date DATE DEFAULT CURRENT_DATE;

-- 2. 기존 데이터에 대해 기본값 설정
UPDATE public.properties 
SET is_active = TRUE 
WHERE is_active IS NULL;

UPDATE public.properties 
SET last_seen_date = collected_date 
WHERE last_seen_date IS NULL;

-- 3. 인덱스 추가 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_properties_is_active ON public.properties(is_active);
CREATE INDEX IF NOT EXISTS idx_properties_deleted_at ON public.properties(deleted_at);
CREATE INDEX IF NOT EXISTS idx_properties_last_seen_date ON public.properties(last_seen_date);

-- 4. 활성 매물만 조회하는 뷰 생성 (선택사항)
CREATE OR REPLACE VIEW active_properties AS
SELECT * FROM public.properties 
WHERE is_active = TRUE;

COMMIT;

-- 5. 스키마 변경 확인
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'properties' 
    AND column_name IN ('is_active', 'deleted_at', 'deletion_reason', 'last_seen_date')
ORDER BY column_name;