"""
오디오 싱크 및 비트 감지 모듈
"""
import numpy as np
from moviepy import AudioFileClip
from typing import List, Optional
from pathlib import Path

def detect_beats(audio_path: Path, min_interval: float = 0.5) -> List[float]:
    """
    오디오 파일에서 비트(에너지 피크)를 감지하여 타임스탬프 리스트 반환
    (간단한 에너지 기반 감지)
    
    Args:
        audio_path: 오디오 파일 경로
        min_interval: 비트 간 최소 간격 (초)
        
    Returns:
        비트 타임스탬프 리스트 (초)
    """
    try:
        # moviepy로 오디오 로드 및 데이터 추출
        # fps=22050으로 리샘플링하여 로드
        fps = 22050
        with AudioFileClip(str(audio_path)) as audio:
            # (N, nchannels) 형태의 배열 반환 (-1.0 ~ 1.0)
            samples = audio.to_soundarray(fps=fps)
            
        # 모노로 변환 (채널 평균)
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
            
        # numpy 배열 확인 (이미 numpy 배열임)

        
        # 윈도우 크기 (약 50ms)
        window_size = int(22050 * 0.05)
        
        # 에너지 계산 (RMS)
        energies = []
        for i in range(0, len(samples), window_size):
            chunk = samples[i:i+window_size]
            if len(chunk) == 0:
                break
            rms = np.sqrt(np.mean(chunk**2))
            energies.append(rms)
        
        energies = np.array(energies)
        
        # 임계값 설정 (평균 + 표준편차 * 계수)
        threshold = np.mean(energies) + np.std(energies) * 1.5
        
        # 피크 찾기
        beats = []
        last_beat_time = -min_interval
        
        for i, energy in enumerate(energies):
            if energy > threshold:
                time = i * 0.05  # 50ms 윈도우
                if time - last_beat_time >= min_interval:
                    beats.append(time)
                    last_beat_time = time
        
        print(f"[Audio] 감지된 비트 수: {len(beats)}")
        return beats
        
    except Exception as e:
        print(f"[Audio] 비트 감지 실패: {e}")
        return []

def adjust_clips_to_beats(clips: List, beats: List[float], total_duration: float) -> List:
    """
    클립들의 길이를 비트에 맞춰 조정
    
    Args:
        clips: 비디오 클립 리스트
        beats: 비트 타임스탬프 리스트
        total_duration: 전체 오디오 길이
        
    Returns:
        길이가 조정된 클립 리스트
    """
    if not beats:
        return clips
    
    new_clips = []
    current_time = 0.0
    beat_idx = 0
    
    for i, clip in enumerate(clips):
        # 현재 시간 이후의 다음 비트 찾기
        next_beat = None
        while beat_idx < len(beats):
            if beats[beat_idx] > current_time + 0.5: # 최소 0.5초 보장
                next_beat = beats[beat_idx]
                break
            beat_idx += 1
        
        # 비트가 없거나 마지막 클립인 경우 남은 시간 또는 기본값 사용
        if next_beat is None or i == len(clips) - 1:
            duration = clip.duration
        else:
            duration = next_beat - current_time
        
        # 클립 길이 조정
        new_clip = clip.with_duration(duration)
        new_clips.append(new_clip)
        
        current_time += duration
    
    return new_clips
