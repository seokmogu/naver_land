class ArticleParser:
    """매물 상세정보 파싱 및 정규화"""

    def __init__(self, address_converter=None):
        self.address_converter = address_converter

    def extract_useful_details(self, detail_data):
        if not detail_data:
            return None

        article_detail = detail_data.get('articleDetail', {})
        article_addition = detail_data.get('articleAddition', {})

        converted_address = None
        lat, lon = article_detail.get('latitude'), article_detail.get('longitude')
        if self.address_converter and lat and lon:
            try:
                converted_address = self.address_converter.convert_coord_to_address(str(lat), str(lon))
            except Exception:
                pass

        useful_info = {
            "건물정보": {
                "법적용도": article_detail.get('lawUsage'),
                "주차대수": article_detail.get('parkingCount'),
                "주차가능": "예" if article_detail.get('parkingPossibleYN') == 'Y' else "아니오",
                "엘리베이터": "있음" if "엘리베이터" in article_detail.get('tagList', []) else "없음",
                "층구조": article_detail.get('floorLayerName')
            },
            "위치정보": {
                "위도": lat,
                "경도": lon,
                "상세주소": article_detail.get('exposureAddress'),
                "지하철도보시간": f"{article_detail.get('walkingTimeToNearSubway', 0)}분"
            },
            "비용정보": {
                "월관리비": article_detail.get('monthlyManagementCost'),
                "관리비포함": article_detail.get('manageCostIncludeItemDesc')
            },
            "입주정보": {
                "입주가능일": article_detail.get('moveInTypeName'),
                "협의가능": article_detail.get('moveInDiscussionPossibleYN')
            },
            "이미지": {
                "현장사진수": article_addition.get('siteImageCount', 0),
                "대표이미지": article_addition.get('representativeImgUrl'),
                "추가사진": detail_data.get('articlePhotos', [])
            },
            "주변시세": {
                "동일주소매물수": article_addition.get('sameAddrCnt', 0),
                "최고가": article_addition.get('sameAddrMaxPrc'),
                "최저가": article_addition.get('sameAddrMinPrc')
            },
            "상세설명": (article_detail.get('detailDescription') or '').strip()[:200],
            "시설정보": detail_data.get('articleFacility', {}),
            "가격정보": detail_data.get('articlePrice', {}),
            "중개사정보": detail_data.get('articleRealtor', {}),
            "층정보": detail_data.get('articleFloor', {}),
            "공간정보": detail_data.get('articleSpace', {}),
            "세금정보": detail_data.get('articleTax', {})
        }

        if converted_address:
            useful_info["카카오주소변환"] = converted_address

        return useful_info
