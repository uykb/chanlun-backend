import datetime
from typing import List, Union, Dict, Tuple
import pandas as pd
import numpy as np
from chanlun.cl_interface import ICL, Kline, CLKline, FX, BI, XD, ZS, LINE, MACD_INFOS, Config

try:
    from czsc import CZSC
    from czsc.objects import RawBar, Direction
    from czsc.utils.bar_generator import resample_bars
except ImportError:
    print("CZSC library not found. Please install it using 'pip install czsc'")
    CZSC = None
    RawBar = None
    Direction = None

class CL(ICL):
    """
    Open Source Chanlun Implementation using CZSC
    """

    def __init__(
        self,
        code: str,
        frequency: str,
        config: Union[dict, None] = None,
        start_datetime: datetime.datetime = None,
    ):
        self.code = code
        self.frequency = frequency
        self.config = config if config else {}
        self.start_datetime = start_datetime
        
        self._klines: List[Kline] = []
        self._cl_klines: List[CLKline] = []
        self._fxs: List[FX] = []
        self._bis: List[BI] = []
        self._xds: List[XD] = []
        self._zss: List[ZS] = []
        
        self._czsc = None
        self._idx = {"macd": {"dif": [], "dea": [], "hist": []}}

    def process_klines(self, klines: pd.DataFrame):
        """
        计算k线缠论数据
        """
        if CZSC is None:
            raise Exception("CZSC library not installed")

        # 转换 K 线数据
        raw_bars = []
        self._klines = []
        
        # 确保 DataFrame 列名正确
        if 'date' not in klines.columns:
            # 尝试重命名常见列名
            klines = klines.rename(columns={
                'datetime': 'date', 'time': 'date',
                'Open': 'open', 'Close': 'close', 'High': 'high', 'Low': 'low', 'Volume': 'volume'
            })

        for i, row in klines.iterrows():
            dt = pd.to_datetime(row['date'])
            # 构建原始 Kline 对象
            k = Kline(
                index=i,
                date=dt,
                h=float(row['high']),
                l=float(row['low']),
                o=float(row['open']),
                c=float(row['close']),
                a=float(row['volume'])
            )
            self._klines.append(k)

            # 构建 CZSC RawBar
            bar = RawBar(
                symbol=self.code,
                dt=dt,
                id=i,
                freq=self.frequency,
                open=k.o,
                close=k.c,
                high=k.h,
                low=k.l,
                vol=k.a,
                amount=0
            )
            raw_bars.append(bar)

        # 初始化 CZSC
        # 注意：CZSC 的初始化可能需要根据版本调整
        self._czsc = CZSC(raw_bars)
        
        # 转换计算结果到 Chanlun-Pro 的数据结构
        self._convert_czsc_data()
        
        # 计算 MACD 指标 (简单实现，或者使用 TA-Lib)
        self._calculate_macd()

    def _convert_czsc_data(self):
        """
        将 CZSC 的对象转换为 ICL 接口定义的对象
        """
        # 1. 转换分型 (FX)
        self._fxs = []
        if hasattr(self._czsc, 'fx_list'):
            for c_fx in self._czsc.fx_list:
                # 这里需要根据 CZSC 的 FX 结构进行适配
                # 假设 c_fx 有 .dt, .high, .low, .type 等属性
                # 这是一个简化的映射，实际需要查看 CZSC 源码
                fx_type = "ding" if c_fx.mark.value == "d" else "di" # 假设 mark 是枚举
                # 需要找到对应的 CLKline
                # ... 实现细节略，需要根据 CZSC 具体结构填充
                pass

        # 2. 转换笔 (BI)
        self._bis = []
        if hasattr(self._czsc, 'bi_list'):
            for i, c_bi in enumerate(self._czsc.bi_list):
                # 构建 BI 对象
                # start_fx = ...
                # end_fx = ...
                # bi = BI(start=start_fx, end=end_fx, _type=c_bi.direction.value, index=i)
                # self._bis.append(bi)
                pass

        # 3. 转换线段 (XD)
        self._xds = []
        
        # 4. 转换中枢 (ZS)
        self._zss = []

    def _calculate_macd(self):
        """
        计算 MACD
        """
        try:
            import talib
            close = np.array([k.c for k in self._klines])
            dif, dea, hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
            # talib 的 hist 通常是 (dif-dea)*2，有些库是 dif-dea
            self._idx["macd"]["dif"] = dif.tolist()
            self._idx["macd"]["dea"] = dea.tolist()
            self._idx["macd"]["hist"] = (hist * 2).tolist() # 调整倍数以匹配
        except ImportError:
            # 手动计算 MACD
            pass

    def get_code(self) -> str:
        return self.code

    def get_frequency(self) -> str:
        return self.frequency

    def get_config(self) -> dict:
        return self.config

    def get_src_klines(self) -> List[Kline]:
        return self._klines

    def get_klines(self) -> List[Kline]:
        return self._klines

    def get_cl_klines(self) -> List[CLKline]:
        return self._cl_klines

    def get_idx(self) -> dict:
        return self._idx

    def get_fxs(self) -> List[FX]:
        return self._fxs

    def get_bis(self) -> List[BI]:
        return self._bis

    def get_xds(self) -> List[XD]:
        return self._xds

    def get_zsds(self) -> List[XD]:
        return []

    def get_qsds(self) -> List[XD]:
        return []

    def get_bi_zss(self, zs_type: str = None) -> List[ZS]:
        return self._zss

    def get_xd_zss(self, zs_type: str = None) -> List[ZS]:
        return []

    def get_zsd_zss(self) -> List[ZS]:
        return []

    def get_qsd_zss(self) -> List[ZS]:
        return []

    def get_last_bi_zs(self) -> Union[ZS, None]:
        return self._zss[-1] if self._zss else None

    def get_last_xd_zs(self) -> Union[ZS, None]:
        return None

    def create_dn_zs(self, zs_type: str, lines: List[LINE], max_line_num: int = 999, zs_include_last_line=True) -> List[ZS]:
        return []

    def beichi_pz(self, zs: ZS, now_line: LINE) -> Tuple[bool, Union[LINE, None]]:
        return False, None

    def beichi_qs(self, lines: List[LINE], zss: List[ZS], now_line: LINE) -> Tuple[bool, List[LINE]]:
        return False, []

    def zss_is_qs(self, one_zs: ZS, two_zs: ZS) -> Tuple[str, None]:
        return None, None
