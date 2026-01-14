"""
네이버 부동산 매물 수집 프로그램 - 메인 GUI
"""
import sys
import os
from datetime import datetime
from typing import Optional, Tuple, List
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QProgressBar, QMessageBox, QFileDialog, QGroupBox,
    QGridLayout, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from api_client import ApiConfig
from data_collector import DataCollector, Property, Complex
from excel_exporter import ExcelExporter
from utils import geocode_address, parse_coordinates


class CollectionThread(QThread):
    """수집 작업을 위한 스레드"""
    progress = Signal(int, int, str)  # current, total, message
    finished = Signal(list, list)  # properties, complexes
    error = Signal(str)
    property_count_updated = Signal(int)  # 수집된 매물 개수 업데이트
    
    def __init__(self, collector, region_name, center_lat, center_lon, zoom, rlet_tp_cd, trad_tp_cd):
        super().__init__()
        self.collector = collector
        self.region_name = region_name
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.zoom = zoom
        self.rlet_tp_cd = rlet_tp_cd
        self.trad_tp_cd = trad_tp_cd
        self.is_cancelled = False
    
    def run(self):
        try:
            last_count = 0
            
            def progress_callback(current, total, message):
                if not self.is_cancelled:
                    self.progress.emit(current, total, message)
                    # 매물 개수 업데이트
                    if hasattr(self.collector, 'properties'):
                        count = len(self.collector.properties)
                        if count != last_count:
                            self.property_count_updated.emit(count)
            
            properties, complexes = self.collector.collect_properties(
                region_name=self.region_name,
                center_lat=self.center_lat,
                center_lon=self.center_lon,
                zoom=self.zoom,
                rlet_tp_cd=self.rlet_tp_cd,
                trad_tp_cd=self.trad_tp_cd,
                grid_size=3,
                progress_callback=progress_callback
            )
            
            if not self.is_cancelled:
                self.finished.emit(properties, complexes)
        except Exception as e:
            self.error.emit(str(e))
    
    def cancel(self):
        self.is_cancelled = True


class MainWindow(QMainWindow):
    """메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.properties: List[Property] = []
        self.complexes: List[Complex] = []
        self.collection_thread: Optional[CollectionThread] = None
        
        self.init_ui()
        self.setup_collector()
    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("네이버 부동산 매물 수집 프로그램")
        self.setGeometry(100, 100, 1200, 800)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 지역 검색 영역
        search_group = QGroupBox("지역 검색")
        search_layout = QVBoxLayout()
        
        # 지역명 입력
        region_layout = QHBoxLayout()
        region_layout.addWidget(QLabel("지역명:"))
        self.region_input = QLineEdit()
        self.region_input.setPlaceholderText("예: 서울시 강남구 역삼동")
        region_layout.addWidget(self.region_input)
        self.search_btn = QPushButton("검색")
        self.search_btn.clicked.connect(self.search_region)
        region_layout.addWidget(self.search_btn)
        search_layout.addLayout(region_layout)
        
        # 좌표 입력 (선택사항)
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(QLabel("좌표 (선택사항):"))
        coord_layout.addWidget(QLabel("위도:"))
        self.lat_input = QLineEdit()
        self.lat_input.setPlaceholderText("37.4514")
        coord_layout.addWidget(self.lat_input)
        coord_layout.addWidget(QLabel("경도:"))
        self.lon_input = QLineEdit()
        self.lon_input.setPlaceholderText("127.1504")
        coord_layout.addWidget(self.lon_input)
        search_layout.addLayout(coord_layout)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # 수집 옵션 영역
        options_group = QGroupBox("수집 옵션")
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel("부동산 유형:"))
        self.property_type_combo = QComboBox()
        self.property_type_combo.addItems([
            "아파트, 재건축 (APT:JGC)",
            "아파트 (APT)",
            "오피스텔 (OPST)",
            "빌라 (VL)",
            "아파트 분양권 (ABYG)"
        ])
        options_layout.addWidget(self.property_type_combo)
        
        options_layout.addWidget(QLabel("거래 유형:"))
        self.trade_type_combo = QComboBox()
        self.trade_type_combo.addItems(["매매 (A1)", "전세 (B1)", "월세 (B2)"])
        options_layout.addWidget(self.trade_type_combo)
        
        options_layout.addWidget(QLabel("줌 레벨:"))
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(15, 18)
        self.zoom_spin.setValue(17)
        options_layout.addWidget(self.zoom_spin)
        
        options_layout.addStretch()
        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)
        
        # 수집 제어 영역
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("수집 시작")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.start_btn.clicked.connect(self.start_collection)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("수집 중지")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_collection)
        control_layout.addWidget(self.stop_btn)
        
        self.save_btn = QPushButton("엑셀로 저장")
        self.save_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_to_excel)
        control_layout.addWidget(self.save_btn)
        
        control_layout.addStretch()
        main_layout.addLayout(control_layout)
        
        # 진행 상황 영역
        progress_group = QGroupBox("진행 상황")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("대기 중...")
        progress_layout.addWidget(self.status_label)
        
        self.count_label = QLabel("수집된 매물: 0개")
        progress_layout.addWidget(self.count_label)
        
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # 매물 목록 테이블
        table_group = QGroupBox("매물 목록")
        table_layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "매물 ID", "지역명", "단지명", "부동산 유형", "거래 유형",
            "가격(만원)", "가격 표시", "위도", "경도", "관리비 최소", "관리비 최대", "VR 투어"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setSortingEnabled(True)
        table_layout.addWidget(self.table)
        
        table_group.setLayout(table_layout)
        main_layout.addWidget(table_group)
        
        # 통계 정보 영역
        stats_group = QGroupBox("통계 정보")
        stats_layout = QGridLayout()
        
        self.total_label = QLabel("총 매물: 0개")
        stats_layout.addWidget(self.total_label, 0, 0)
        
        self.trade_stats_label = QLabel("매매: 0개 | 전세: 0개 | 월세: 0개")
        stats_layout.addWidget(self.trade_stats_label, 0, 1)
        
        self.price_stats_label = QLabel("평균 가격: - | 최고가: - | 최저가: -")
        stats_layout.addWidget(self.price_stats_label, 1, 0, 1, 2)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
    
    def setup_collector(self):
        """수집기 설정"""
        api_config = ApiConfig(min_delay=1.0, timeout=10, max_retries=3)
        self.collector = DataCollector(api_config)
    
    def search_region(self):
        """지역 검색 및 좌표 변환"""
        region = self.region_input.text().strip()
        if not region:
            QMessageBox.warning(self, "경고", "지역명을 입력하세요.")
            return
        
        # 좌표가 이미 입력되어 있으면 사용
        if self.lat_input.text() and self.lon_input.text():
            coords = parse_coordinates(self.lat_input.text(), self.lon_input.text())
            if coords:
                QMessageBox.information(self, "성공", f"좌표 설정 완료\n위도: {coords[0]}, 경도: {coords[1]}")
                return
        
        # 주소를 좌표로 변환
        self.status_label.setText("좌표 변환 중...")
        coords = geocode_address(region)
        
        if coords:
            self.lat_input.setText(str(coords[0]))
            self.lon_input.setText(str(coords[1]))
            QMessageBox.information(self, "성공", f"좌표 변환 완료\n위도: {coords[0]}, 경도: {coords[1]}")
        else:
            from utils import GEOPY_AVAILABLE
            if not GEOPY_AVAILABLE:
                QMessageBox.warning(
                    self, 
                    "오류", 
                    "geopy 패키지가 설치되지 않았습니다.\n"
                    "좌표를 직접 입력하거나 다음 명령으로 설치하세요:\n"
                    "pip install geopy"
                )
            else:
                QMessageBox.warning(self, "오류", "좌표 변환에 실패했습니다. 좌표를 직접 입력하세요.")
    
    def start_collection(self):
        """수집 시작"""
        # 입력 검증
        region = self.region_input.text().strip()
        if not region:
            QMessageBox.warning(self, "경고", "지역명을 입력하세요.")
            return
        
        if not self.lat_input.text() or not self.lon_input.text():
            QMessageBox.warning(self, "경고", "좌표를 입력하거나 지역 검색을 실행하세요.")
            return
        
        coords = parse_coordinates(self.lat_input.text(), self.lon_input.text())
        if not coords:
            QMessageBox.warning(self, "경고", "유효한 좌표를 입력하세요.")
            return
        
        # 옵션 가져오기
        property_type_map = {
            0: "APT:JGC",
            1: "APT",
            2: "OPST",
            3: "VL",
            4: "ABYG"
        }
        trade_type_map = {
            0: "A1",
            1: "B1",
            2: "B2"
        }
        
        rlet_tp_cd = property_type_map[self.property_type_combo.currentIndex()]
        trad_tp_cd = trade_type_map[self.trade_type_combo.currentIndex()]
        zoom = max(self.zoom_spin.value(), 18)  # 최소 줌 레벨 18로 설정하여 더 많은 개별 매물 수집
        
        # UI 상태 변경
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.save_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.table.setRowCount(0)
        self.properties = []
        self.complexes = []
        
        # 수집 스레드 시작
        self.collection_thread = CollectionThread(
            self.collector,
            region,
            coords[0],
            coords[1],
            zoom,
            rlet_tp_cd,
            trad_tp_cd
        )
        self.collection_thread.progress.connect(self.on_progress)
        self.collection_thread.finished.connect(self.on_finished)
        self.collection_thread.error.connect(self.on_error)
        self.collection_thread.property_count_updated.connect(self.on_property_count_updated)
        self.collection_thread.start()
    
    def stop_collection(self):
        """수집 중지"""
        if self.collection_thread:
            self.collection_thread.cancel()
            self.collection_thread.wait()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("수집 중지됨")
    
    def on_progress(self, current: int, total: int, message: str):
        """진행 상황 업데이트"""
        # total이 100으로 고정되어 있으므로 current를 그대로 사용
        if total == 100:
            progress = current
        else:
            progress = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
    
    def on_property_count_updated(self, count: int):
        """수집된 매물 개수 업데이트"""
        self.count_label.setText(f"수집된 매물: {count}개")
    
    def on_finished(self, properties: List[Property], complexes: List[Complex]):
        """수집 완료"""
        self.properties = properties
        self.complexes = complexes
        
        # 테이블 업데이트
        self.update_table()
        
        # 통계 업데이트
        self.update_stats()
        
        # UI 상태 변경
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.save_btn.setEnabled(True)
        self.status_label.setText(f"수집 완료: {len(properties)}개 매물, {len(complexes)}개 단지")
        self.progress_bar.setValue(100)
        
        QMessageBox.information(self, "완료", f"수집이 완료되었습니다.\n매물: {len(properties)}개\n단지: {len(complexes)}개")
    
    def on_error(self, error_msg: str):
        """오류 처리"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText(f"오류: {error_msg}")
        QMessageBox.critical(self, "오류", f"수집 중 오류가 발생했습니다:\n{error_msg}")
    
    def update_table(self):
        """테이블 업데이트"""
        self.table.setRowCount(len(self.properties))
        
        for row, prop in enumerate(self.properties):
            self.table.setItem(row, 0, QTableWidgetItem(prop.item_id))
            self.table.setItem(row, 1, QTableWidgetItem(prop.region_name))
            self.table.setItem(row, 2, QTableWidgetItem(prop.complex_name))
            self.table.setItem(row, 3, QTableWidgetItem(prop.property_type))
            self.table.setItem(row, 4, QTableWidgetItem(prop.trade_type))
            self.table.setItem(row, 5, QTableWidgetItem(str(prop.price)))
            self.table.setItem(row, 6, QTableWidgetItem(prop.price_display))
            self.table.setItem(row, 7, QTableWidgetItem(f"{prop.latitude:.6f}"))
            self.table.setItem(row, 8, QTableWidgetItem(f"{prop.longitude:.6f}"))
            self.table.setItem(row, 9, QTableWidgetItem(str(prop.min_mvi_fee)))
            self.table.setItem(row, 10, QTableWidgetItem(str(prop.max_mvi_fee)))
            self.table.setItem(row, 11, QTableWidgetItem("예" if prop.tour_exist else "아니오"))
        
        self.count_label.setText(f"수집된 매물: {len(self.properties)}개")
    
    def update_stats(self):
        """통계 정보 업데이트"""
        # 총 개수
        self.total_label.setText(f"총 매물: {len(self.properties)}개")
        
        # 거래 유형별 개수
        trade_counts = {}
        for prop in self.properties:
            trade_type = prop.trade_type
            trade_counts[trade_type] = trade_counts.get(trade_type, 0) + 1
        
        self.trade_stats_label.setText(
            f"매매: {trade_counts.get('매매', 0)}개 | "
            f"전세: {trade_counts.get('전세', 0)}개 | "
            f"월세: {trade_counts.get('월세', 0)}개"
        )
        
        # 가격 통계
        prices = [p.price for p in self.properties if p.price > 0]
        if prices:
            avg_price = sum(prices) / len(prices)
            max_price = max(prices)
            min_price = min(prices)
            
            def format_price(price):
                if price >= 10000:
                    return f"{price/10000:.1f}억"
                else:
                    return f"{price:,.0f}만원"
            
            self.price_stats_label.setText(
                f"평균 가격: {format_price(avg_price)} | "
                f"최고가: {format_price(max_price)} | "
                f"최저가: {format_price(min_price)}"
            )
        else:
            self.price_stats_label.setText("평균 가격: - | 최고가: - | 최저가: -")
    
    def save_to_excel(self):
        """엑셀 파일로 저장"""
        if not self.properties and not self.complexes:
            QMessageBox.warning(self, "경고", "저장할 데이터가 없습니다.")
            return
        
        # 파일 저장 대화상자
        region_name = self.region_input.text().strip() or "지역"
        safe_region = "".join(c for c in region_name if c.isalnum() or c in (' ', '-', '_'))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{safe_region}_매물정보_{timestamp}.xlsx"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "엑셀 파일 저장",
            default_filename,
            "Excel Files (*.xlsx)"
        )
        
        if filename:
            try:
                exporter = ExcelExporter()
                exporter.export(
                    filename=filename,
                    properties=self.properties,
                    complexes=self.complexes,
                    region_name=region_name,
                    include_properties=True,
                    include_complexes=True
                )
                QMessageBox.information(self, "성공", f"파일이 저장되었습니다:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"파일 저장 중 오류가 발생했습니다:\n{str(e)}")


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 스타일 설정
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

