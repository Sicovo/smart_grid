import argparse
from collections import deque
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import requests


@dataclass
class Config:
	base_url: str = "https://icelec50015.azurewebsites.net"
	interval_ms: int = 5000
	timeout_s: float = 5.0
	live_window: int = 120


class SmartGridGrapher:
	def __init__(self, config: Config) -> None:
		self.config = config
		self.session = requests.Session()
		self.anim = None
		self.update_count = 0

		self.live_tick: deque[int] = deque(maxlen=config.live_window)
		self.live_demand: deque[float] = deque(maxlen=config.live_window)
		self.live_sun: deque[float] = deque(maxlen=config.live_window)
		self.live_buy: deque[float] = deque(maxlen=config.live_window)
		self.live_sell: deque[float] = deque(maxlen=config.live_window)

		self.deferables: list[dict[str, Any]] = []
		self.yesterday: list[dict[str, Any]] = []
		self.last_error = ""

		self.fig, self.axes = plt.subplots(2, 2, figsize=(14, 8), constrained_layout=True)
		self.fig.suptitle("Smart Grid Live Graphing", fontsize=14)

	def _get_json(self, path: str) -> Any:
		url = self.config.base_url.rstrip("/") + path
		response = self.session.get(url, timeout=self.config.timeout_s)
		response.raise_for_status()
		return response.json()

	def fetch(self) -> None:
		demand = self._get_json("/demand")
		sun = self._get_json("/sun")
		price = self._get_json("/price")
		self.deferables = self._get_json("/deferables")

		# /yesterday changes only once per cycle/day, but this keeps the view in sync.
		self.yesterday = self._get_json("/yesterday")

		tick = int(demand.get("tick", 0))
		self.live_tick.append(tick)
		self.live_demand.append(float(demand.get("demand", 0.0)))
		self.live_sun.append(float(sun.get("sun", 0.0)) / 100.0)
		self.live_buy.append(float(price.get("buy_price", 0.0)))
		self.live_sell.append(float(price.get("sell_price", 0.0)))

		self.last_error = ""

	def _draw_live_panel(self, ax: Any) -> None:
		ax.clear()
		if not self.live_tick:
			ax.set_title("Live Signals")
			ax.text(0.5, 0.5, "Waiting for data...", ha="center", va="center", transform=ax.transAxes)
			return

		ticks = list(self.live_tick)
		ax.plot(ticks, list(self.live_demand), label="Instant Demand (kW)", color="#1f77b4", linewidth=2)
		ax.plot(ticks, list(self.live_sun), label="Irradiance (fraction)", color="#ff7f0e", linewidth=2)
		ax.set_title("Live Demand and Irradiance")
		ax.set_xlabel("Tick")
		ax.set_ylabel("Demand / Irradiance")
		ax.grid(True, alpha=0.3)

		ax_price = ax.twinx()
		ax_price.plot(ticks, list(self.live_buy), label="Buy Price", color="#2ca02c", linestyle="--")
		ax_price.plot(ticks, list(self.live_sell), label="Sell Price", color="#d62728", linestyle="--")
		ax_price.set_ylabel("Price")

		handles_left, labels_left = ax.get_legend_handles_labels()
		handles_right, labels_right = ax_price.get_legend_handles_labels()
		ax.legend(handles_left + handles_right, labels_left + labels_right, loc="upper left")
		ax.text(
			0.99,
			0.02,
			f"Last update tick: {ticks[-1]} | refresh #{self.update_count}",
			ha="right",
			va="bottom",
			transform=ax.transAxes,
			fontsize=9,
			color="#333333",
		)

	def _draw_deferables_panel(self, ax: Any) -> None:
		ax.clear()
		ax.set_title("Deferrable Demand Windows")
		ax.set_xlabel("Tick")
		ax.set_ylabel("Task")
		ax.set_xlim(0, 59)
		ax.grid(True, axis="x", alpha=0.3)

		if not self.deferables:
			ax.text(0.5, 0.5, "No deferrable demands available", ha="center", va="center", transform=ax.transAxes)
			return

		current_tick = self.live_tick[-1] if self.live_tick else 0
		y_positions = list(range(len(self.deferables)))
		labels = []

		for idx, item in enumerate(self.deferables):
			start = int(item.get("start", 0))
			end = int(item.get("end", start))
			energy = float(item.get("energy", 0.0))
			width = max(1, end - start + 1)
			active = start <= current_tick <= end
			color = "#9467bd" if active else "#8c8c8c"
			ax.broken_barh([(start, width)], (idx - 0.4, 0.8), facecolors=color)
			labels.append(f"T{idx}: {energy:.1f} kWh")

		ax.set_yticks(y_positions)
		ax.set_yticklabels(labels)
		ax.axvline(current_tick, color="#111111", linewidth=1.5, linestyle=":", label=f"Current tick {current_tick}")
		ax.legend(loc="lower right")

	def _draw_yesterday_panel(self, ax: Any) -> None:
		ax.clear()
		ax.set_title("Yesterday: Demand and Prices")
		ax.set_xlabel("Tick")

		if not self.yesterday:
			ax.text(0.5, 0.5, "No yesterday data available", ha="center", va="center", transform=ax.transAxes)
			return

		ticks = [int(item.get("tick", 0)) for item in self.yesterday]
		demand = [float(item.get("demand", 0.0)) for item in self.yesterday]
		buy = [float(item.get("buy_price", 0.0)) for item in self.yesterday]
		sell = [float(item.get("sell_price", 0.0)) for item in self.yesterday]

		ax.plot(ticks, demand, color="#1f77b4", linewidth=1.8, label="Demand")
		ax.set_ylabel("Demand")
		ax.grid(True, alpha=0.3)

		ax2 = ax.twinx()
		ax2.plot(ticks, buy, color="#2ca02c", linestyle="--", label="Buy")
		ax2.plot(ticks, sell, color="#d62728", linestyle="--", label="Sell")
		ax2.set_ylabel("Price")

		h1, l1 = ax.get_legend_handles_labels()
		h2, l2 = ax2.get_legend_handles_labels()
		ax.legend(h1 + h2, l1 + l2, loc="upper left")

	def _draw_summary_panel(self, ax: Any) -> None:
		ax.clear()
		ax.axis("off")
		ax.set_title("Current Summary")

		if not self.live_tick:
			ax.text(0.03, 0.9, "Waiting for first tick...", fontsize=11, va="top")
			return

		tick = self.live_tick[-1]
		demand = self.live_demand[-1]
		sun = self.live_sun[-1]
		buy = self.live_buy[-1]
		sell = self.live_sell[-1]

		remaining_energy = 0.0
		active_jobs = 0
		for item in self.deferables:
			end = int(item.get("end", -1))
			start = int(item.get("start", 0))
			energy = float(item.get("energy", 0.0))
			if tick <= end:
				remaining_energy += energy
			if start <= tick <= end:
				active_jobs += 1

		lines = [
			f"Tick: {tick}",
			f"Instant demand: {demand:.3f}",
			f"Irradiance fraction: {sun:.2f}",
			f"Buy price: {buy:.2f}",
			f"Sell price: {sell:.2f}",
			f"Deferrable jobs: {len(self.deferables)}",
			f"Active windows now: {active_jobs}",
			f"Remaining deferrable energy: {remaining_energy:.2f}",
		]

		if self.last_error:
			lines.append("")
			lines.append(f"Last fetch error: {self.last_error}")

		ax.text(0.03, 0.95, "\n".join(lines), va="top", fontsize=11)

	def update(self, _frame: int) -> list[Any]:
		self.update_count += 1
		try:
			self.fetch()
		except requests.RequestException as exc:
			self.last_error = str(exc)

		self._draw_live_panel(self.axes[0, 0])
		self._draw_deferables_panel(self.axes[0, 1])
		self._draw_yesterday_panel(self.axes[1, 0])
		self._draw_summary_panel(self.axes[1, 1])
		return []

	def run(self) -> None:
		self.update(0)
		# Keep a strong reference to the animation to avoid premature GC.
		self.anim = FuncAnimation(
			self.fig,
			self.update,
			interval=self.config.interval_ms,
			cache_frame_data=False,
		)
		plt.show()


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Live graphing for Smart Grid webserver data")
	parser.add_argument(
		"--base-url",
		default="https://icelec50015.azurewebsites.net",
		help="Base URL for the smart-grid information server",
	)
	parser.add_argument(
		"--interval-ms",
		type=int,
		default=5000,
		help="Plot update interval in milliseconds",
	)
	parser.add_argument(
		"--timeout",
		type=float,
		default=5.0,
		help="HTTP request timeout in seconds",
	)
	parser.add_argument(
		"--window",
		type=int,
		default=120,
		help="Number of live ticks to keep in memory",
	)
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	config = Config(
		base_url=args.base_url,
		interval_ms=args.interval_ms,
		timeout_s=args.timeout,
		live_window=args.window,
	)
	SmartGridGrapher(config).run()


if __name__ == "__main__":
	main()
