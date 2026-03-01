"""
風格分析 API 路由

提供 FFT 風格分析結果、特徵說明、雷達圖數據等
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path

router = APIRouter()
PROJECT_ROOT = Path(__file__).parent.parent.parent


@router.get("/images")
async def analysis_images():
    """取得風格分析圖片 URL（預先生成的圖片）"""
    try:
        from web.services.analysis_service import get_analysis_images
        data = get_analysis_images()
        if data is None:
            raise HTTPException(status_code=404, detail="分析圖片尚未生成，請先執行風格分析")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得分析圖片失敗：{e}")


@router.get("/features")
async def analysis_features():
    """取得 7 個 FFT 特徵的詳細說明"""
    try:
        from web.services.analysis_service import get_feature_descriptions
        data = get_feature_descriptions()
        if data is None:
            raise HTTPException(status_code=404, detail="特徵說明資料不存在")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得特徵說明失敗：{e}")


@router.get("/radar-data")
async def radar_data():
    """取得雷達圖 JSON 數據（用於前端互動式繪圖）"""
    try:
        from web.services.analysis_service import get_radar_chart_data
        data = get_radar_chart_data()
        if data is None:
            return {
                "available": False,
                "message": "風格分析數據尚未生成，請先執行 FFT 風格分析",
            }
        return {"available": True, **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得雷達圖數據失敗：{e}")


@router.get("/similarity")
async def similarity_data():
    """取得相似度矩陣數據"""
    try:
        from web.services.analysis_service import get_similarity_data
        data = get_similarity_data()
        if data is None:
            return {
                "available": False,
                "message": "相似度數據尚未生成",
            }
        return {"available": True, **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得相似度數據失敗：{e}")
