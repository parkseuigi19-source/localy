"""
작업 상태 관리 시스템
"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from models import JobStatus, JobStatusResponse
from config import JOBS_DIR, UPLOAD_DIR, OUTPUT_DIR


class JobManager:
    """작업 상태를 JSON 파일로 관리"""
    
    def __init__(self):
        self.jobs_dir = JOBS_DIR
        self.upload_dir = UPLOAD_DIR
        self.output_dir = OUTPUT_DIR
    
    def create_job(self, photo_count: int) -> str:
        """
        새 작업 생성
        
        Args:
            photo_count: 업로드된 사진 개수
            
        Returns:
            생성된 작업 ID
        """
        job_id = str(uuid.uuid4())
        
        # 작업 디렉토리 생성
        job_upload_dir = self.upload_dir / job_id
        job_output_dir = self.output_dir / job_id
        job_upload_dir.mkdir(parents=True, exist_ok=True)
        job_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 작업 상태 초기화
        job_data = {
            "job_id": job_id,
            "status": JobStatus.PENDING.value,
            "progress": 0,
            "message": "작업이 생성되었습니다.",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None,
            "error": None,
            "output_file": None,
            "metadata": {
                "photo_count": photo_count,
                "upload_dir": str(job_upload_dir),
                "output_dir": str(job_output_dir),
            }
        }
        
        # JSON 파일로 저장
        job_file = self.jobs_dir / f"{job_id}.json"
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, ensure_ascii=False, indent=2)
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[JobStatusResponse]:
        """
        작업 상태 조회
        
        Args:
            job_id: 작업 ID
            
        Returns:
            작업 상태 정보 또는 None
        """
        job_file = self.jobs_dir / f"{job_id}.json"
        
        if not job_file.exists():
            return None
        
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        return JobStatusResponse(**job_data)
    
    def update_job_status(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        output_file: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        작업 상태 업데이트
        
        Args:
            job_id: 작업 ID
            status: 새로운 상태
            progress: 진행률 (0-100)
            message: 상태 메시지
            error: 에러 메시지
            output_file: 출력 파일 경로
            metadata: 추가 메타데이터
            
        Returns:
            업데이트 성공 여부
        """
        job_file = self.jobs_dir / f"{job_id}.json"
        
        if not job_file.exists():
            return False
        
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # 업데이트
        if status is not None:
            job_data["status"] = status.value
        if progress is not None:
            job_data["progress"] = progress
        if message is not None:
            job_data["message"] = message
        if error is not None:
            job_data["error"] = error
        if output_file is not None:
            job_data["output_file"] = output_file
        if metadata is not None:
            if job_data["metadata"] is None:
                job_data["metadata"] = {}
            job_data["metadata"].update(metadata)
        
        job_data["updated_at"] = datetime.now().isoformat()
        
        # 완료 시간 기록
        if status == JobStatus.COMPLETED or status == JobStatus.FAILED:
            job_data["completed_at"] = datetime.now().isoformat()
        
        # 저장
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, ensure_ascii=False, indent=2)
        
        return True
    
    def get_job_upload_dir(self, job_id: str) -> Optional[Path]:
        """작업의 업로드 디렉토리 경로 반환"""
        job_status = self.get_job_status(job_id)
        if job_status and job_status.metadata:
            return Path(job_status.metadata.get("upload_dir", ""))
        return None
    
    def get_job_output_dir(self, job_id: str) -> Optional[Path]:
        """작업의 출력 디렉토리 경로 반환"""
        job_status = self.get_job_status(job_id)
        if job_status and job_status.metadata:
            return Path(job_status.metadata.get("output_dir", ""))
        return None
    
    def delete_job(self, job_id: str) -> bool:
        """
        작업 및 관련 파일 삭제
        
        Args:
            job_id: 작업 ID
            
        Returns:
            삭제 성공 여부
        """
        import shutil
        
        job_file = self.jobs_dir / f"{job_id}.json"
        
        if not job_file.exists():
            return False
        
        # 업로드 및 출력 디렉토리 삭제
        job_upload_dir = self.upload_dir / job_id
        job_output_dir = self.output_dir / job_id
        
        if job_upload_dir.exists():
            shutil.rmtree(job_upload_dir)
        if job_output_dir.exists():
            shutil.rmtree(job_output_dir)
        
        # 작업 파일 삭제
        job_file.unlink()
        
        return True


# 싱글톤 인스턴스
job_manager = JobManager()
