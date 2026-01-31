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
        # 辅助函数：根据时间查找 K 线索引
        date_to_index = {k.date: i for i, k in enumerate(self._klines)}

        def get_k_by_date(date):
            idx = date_to_index.get(date)
            return self._klines[idx] if idx is not None else None

        def create_cl_kline(k_index, date, h, l, o, c, a):
            # 创建一个简单的 CLKline，不包含合并细节
            return CLKline(
                k_index=k_index,
                date=date,
                h=h, l=l, o=o, c=c, a=a,
                klines=[self._klines[k_index]] if k_index < len(self._klines) else [],
                index=0, _n=1, _q=False
            )

        # 1. 转换分型 (FX)
        self._fxs = []
        # CZSC 的 fx_list 存储在 analyzer 对象中，通常是 czsc.fx_list
        # 假设 czsc 是 CZSC 实例
        if hasattr(self._czsc, 'fx_list'):
            for i, c_fx in enumerate(self._czsc.fx_list):
                # c_fx 属性: dt, high, low, mark (d/g)
                k_index = date_to_index.get(c_fx.dt, 0)
                cl_kline = create_cl_kline(k_index, c_fx.dt, c_fx.high, c_fx.low, c_fx.high, c_fx.low, 0)
                
                fx_type = "ding" if c_fx.mark.value == "g" else "di"
                
                fx = FX(
                    _type=fx_type,
                    k=cl_kline,
                    klines=[cl_kline], # 简化处理
                    val=c_fx.high if fx_type == "ding" else c_fx.low,
                    index=i,
                    done=True
                )
                self._fxs.append(fx)

        # 2. 转换笔 (BI)
        self._bis = []
        if hasattr(self._czsc, 'bi_list'):
            for i, c_bi in enumerate(self._czsc.bi_list):
                # c_bi 属性: fx_a, fx_b, high, low, direction
                # 查找对应的 FX 对象
                start_fx = next((f for f in self._fxs if f.k.date == c_bi.fx_a.dt), None)
                end_fx = next((f for f in self._fxs if f.k.date == c_bi.fx_b.dt), None)
                
                if start_fx and end_fx:
                    bi_type = "up" if c_bi.direction.value == "up" else "down"
                    bi = BI(
                        start=start_fx,
                        end=end_fx,
                        _type=bi_type,
                        index=i
                    )
                    bi.high = c_bi.high
                    bi.low = c_bi.low
                    self._bis.append(bi)

        # 3. 转换线段 (XD)
        self._xds = []
        if hasattr(self._czsc, 'xd_list'):
             for i, c_xd in enumerate(self._czsc.xd_list):
                # c_xd 属性: start_bi, end_bi, high, low, direction
                # 这里的 start/end 是笔，我们需要找到对应的分型
                # 假设 c_xd.start_bi 是笔对象，我们取它的 start_fx
                # 注意：CZSC 的线段定义可能与 Chanlun-Pro 略有不同，这里做近似映射
                
                # 尝试通过时间匹配笔
                start_bi_dt = c_xd.start_bi.fx_a.dt
                end_bi_dt = c_xd.end_bi.fx_b.dt
                
                # 在 self._bis 中找到对应的笔（可选，用于设置 start_line/end_line）
                # 这里简化，直接找分型
                start_fx = next((f for f in self._fxs if f.k.date == start_bi_dt), None)
                end_fx = next((f for f in self._fxs if f.k.date == end_bi_dt), None)

                if start_fx and end_fx:
                    xd_type = "up" if c_xd.direction.value == "up" else "down"
                    # 创建一个虚拟的 start_line (BI)
                    start_line = BI(start=start_fx, end=start_fx, _type="up", index=0) # 占位

                    xd = XD(
                        start=start_fx,
                        end=end_fx,
                        start_line=start_line, # 必填
                        _type=xd_type,
                        index=i
                    )
                    xd.high = c_xd.high
                    xd.low = c_xd.low
                    self._xds.append(xd)

        # 4. 转换中枢 (ZS)
        self._zss = []
        # CZSC 可能没有直接的 zs_list，或者叫其他名字，如 bi_zs_list
        # 假设有 bi_zs_list (笔中枢)
        if hasattr(self._czsc, 'bi_zs_list'):
            for i, c_zs in enumerate(self._czsc.bi_zs_list):
                # c_zs 属性: start_bi, end_bi, zg, zd, gg, dd
                start_dt = c_zs.start_bi.fx_a.dt
                end_dt = c_zs.end_bi.fx_b.dt
                
                start_fx = next((f for f in self._fxs if f.k.date == start_dt), None)
                end_fx = next((f for f in self._fxs if f.k.date == end_dt), None)
                
                if start_fx and end_fx:
                    zs = ZS(
                        zs_type="bi",
                        start=start_fx,
                        end=end_fx,
                        zg=c_zs.zg,
                        zd=c_zs.zd,
                        gg=c_zs.gg,
                        dd=c_zs.dd,
                        _type="zd", # 默认为震荡
                        index=i
                    )
                    self._zss.append(zs)

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
