"""
Programa interactivo para crear y ejecutar órdenes personalizadas.

Este programa permite:
- Crear órdenes de mercado, límite y stop personalizadas
- Ejecutar las órdenes en TWS
- Ver el estado de las órdenes
- Cancelar órdenes
- Ver posiciones actuales
"""

import asyncio
import logging
from decimal import Decimal
from typing import Optional

from execution import (
    IBKRConnectionManager,
    IBKROrderExecutor,
    OrderRequest,
    OrderType,
    Side,
    TimeInForce,
    RiskCheckError,
    OrderRejectedError,
    ConnectionError,
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class InteractiveOrderTester:
    """Probador interactivo de órdenes."""

    def __init__(self):
        self.manager: Optional[IBKRConnectionManager] = None
        self.executor: Optional[IBKROrderExecutor] = None
        self.submitted_orders = []

    async def connect(self, host: str = "127.0.0.1", port: int = 7497):
        """Conectar a TWS."""
        print(f"\n🔌 Conectando a TWS en {host}:{port}...")
        self.manager = IBKRConnectionManager(host=host, port=port, client_id=1)
        
        try:
            await self.manager.connect()
            self.executor = IBKROrderExecutor(connection_manager=self.manager)
            print("✅ Conectado exitosamente!")
            return True
        except ConnectionError as e:
            print(f"❌ Error de conexión: {e}")
            print("\n💡 Asegúrate de que TWS esté ejecutándose y el API esté habilitado.")
            return False

    async def disconnect(self):
        """Desconectar de TWS."""
        if self.manager:
            await self.manager.disconnect()
            print("✅ Desconectado de TWS")

    def print_menu(self):
        """Mostrar menú principal."""
        print("\n" + "="*60)
        print("📊 PROBADOR DE ÓRDENES IBKR")
        print("="*60)
        print("1. 📈 Crear orden de MERCADO (Market Order)")
        print("2. 📊 Crear orden LÍMITE (Limit Order)")
        print("3. 🛑 Crear orden STOP")
        print("4. 🔄 Crear orden STOP-LÍMITE")
        print("5. 📋 Ver órdenes abiertas")
        print("6. ❌ Cancelar una orden")
        print("7. 💼 Ver posiciones actuales")
        print("8. 📝 Ver historial de órdenes enviadas")
        print("9. 🚪 Salir")
        print("="*60)

    async def create_market_order(self):
        """Crear y ejecutar orden de mercado."""
        print("\n📈 ORDEN DE MERCADO")
        print("-" * 40)
        
        symbol = input("Símbolo (ej: AAPL): ").strip().upper()
        side = input("Compra o Venta (B/S): ").strip().upper()
        quantity = input("Cantidad: ").strip()
        
        if side not in ['B', 'S']:
            print("❌ Lado inválido. Use B para compra o S para venta.")
            return
        
        try:
            request = OrderRequest(
                symbol=symbol,
                quantity=Decimal(quantity),
                order_type=OrderType.MARKET,
                side=Side.BUY if side == 'B' else Side.SELL,
                client_order_id=f"market-{len(self.submitted_orders)+1}"
            )
            
            print(f"\n📤 Enviando orden: {side} {quantity} {symbol} @ MERCADO")
            order = await self.executor.submit_order(request)
            self.submitted_orders.append(order)
            
            print(f"✅ Orden enviada!")
            print(f"   Order ID: {order.order_id}")
            print(f"   Estado: {order.status.value}")
            
        except (RiskCheckError, OrderRejectedError) as e:
            print(f"❌ Orden rechazada: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")

    async def create_limit_order(self):
        """Crear y ejecutar orden límite."""
        print("\n📊 ORDEN LÍMITE")
        print("-" * 40)
        
        symbol = input("Símbolo (ej: TSLA): ").strip().upper()
        side = input("Compra o Venta (B/S): ").strip().upper()
        quantity = input("Cantidad: ").strip()
        limit_price = input("Precio límite: ").strip()
        tif = input("Time in Force (DAY/GTC) [DAY]: ").strip().upper() or "DAY"
        
        if side not in ['B', 'S']:
            print("❌ Lado inválido. Use B para compra o S para venta.")
            return
        
        try:
            time_in_force = TimeInForce.GTC if tif == "GTC" else TimeInForce.DAY
            
            request = OrderRequest(
                symbol=symbol,
                quantity=Decimal(quantity),
                order_type=OrderType.LIMIT,
                side=Side.BUY if side == 'B' else Side.SELL,
                limit_price=Decimal(limit_price),
                time_in_force=time_in_force,
                client_order_id=f"limit-{len(self.submitted_orders)+1}"
            )
            
            print(f"\n📤 Enviando orden: {side} {quantity} {symbol} @ ${limit_price} ({tif})")
            order = await self.executor.submit_order(request)
            self.submitted_orders.append(order)
            
            print(f"✅ Orden enviada!")
            print(f"   Order ID: {order.order_id}")
            print(f"   Estado: {order.status.value}")
            
        except (RiskCheckError, OrderRejectedError) as e:
            print(f"❌ Orden rechazada: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")

    async def create_stop_order(self):
        """Crear y ejecutar orden stop."""
        print("\n🛑 ORDEN STOP")
        print("-" * 40)
        
        symbol = input("Símbolo (ej: SPY): ").strip().upper()
        side = input("Compra o Venta (B/S): ").strip().upper()
        quantity = input("Cantidad: ").strip()
        stop_price = input("Precio stop: ").strip()
        
        if side not in ['B', 'S']:
            print("❌ Lado inválido. Use B para compra o S para venta.")
            return
        
        try:
            request = OrderRequest(
                symbol=symbol,
                quantity=Decimal(quantity),
                order_type=OrderType.STOP,
                side=Side.BUY if side == 'B' else Side.SELL,
                stop_price=Decimal(stop_price),
                client_order_id=f"stop-{len(self.submitted_orders)+1}"
            )
            
            print(f"\n📤 Enviando orden: {side} {quantity} {symbol} STOP @ ${stop_price}")
            order = await self.executor.submit_order(request)
            self.submitted_orders.append(order)
            
            print(f"✅ Orden enviada!")
            print(f"   Order ID: {order.order_id}")
            print(f"   Estado: {order.status.value}")
            
        except (RiskCheckError, OrderRejectedError) as e:
            print(f"❌ Orden rechazada: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")

    async def create_stop_limit_order(self):
        """Crear y ejecutar orden stop-límite."""
        print("\n🔄 ORDEN STOP-LÍMITE")
        print("-" * 40)
        
        symbol = input("Símbolo (ej: QQQ): ").strip().upper()
        side = input("Compra o Venta (B/S): ").strip().upper()
        quantity = input("Cantidad: ").strip()
        stop_price = input("Precio stop (trigger): ").strip()
        limit_price = input("Precio límite: ").strip()
        
        if side not in ['B', 'S']:
            print("❌ Lado inválido. Use B para compra o S para venta.")
            return
        
        try:
            request = OrderRequest(
                symbol=symbol,
                quantity=Decimal(quantity),
                order_type=OrderType.STOP_LIMIT,
                side=Side.BUY if side == 'B' else Side.SELL,
                stop_price=Decimal(stop_price),
                limit_price=Decimal(limit_price),
                client_order_id=f"stop-limit-{len(self.submitted_orders)+1}"
            )
            
            print(f"\n📤 Enviando orden: {side} {quantity} {symbol} STOP-LIMIT "
                  f"@ STOP ${stop_price} / LIMIT ${limit_price}")
            order = await self.executor.submit_order(request)
            self.submitted_orders.append(order)
            
            print(f"✅ Orden enviada!")
            print(f"   Order ID: {order.order_id}")
            print(f"   Estado: {order.status.value}")
            
        except (RiskCheckError, OrderRejectedError) as e:
            print(f"❌ Orden rechazada: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")

    async def view_open_orders(self):
        """Ver órdenes abiertas."""
        print("\n📋 ÓRDENES ABIERTAS")
        print("-" * 60)
        
        try:
            orders = await self.executor.get_open_orders()
            
            if not orders:
                print("No hay órdenes abiertas.")
                return
            
            for i, order in enumerate(orders, 1):
                print(f"\n{i}. Order ID: {order.order_id}")
                print(f"   Símbolo: {order.symbol}")
                print(f"   Tipo: {order.order_type.value}")
                print(f"   Lado: {order.side.value}")
                print(f"   Cantidad: {order.quantity}")
                if order.limit_price:
                    print(f"   Precio límite: ${order.limit_price}")
                if order.stop_price:
                    print(f"   Precio stop: ${order.stop_price}")
                print(f"   Estado: {order.status.value}")
                print(f"   Cantidad ejecutada: {order.filled_quantity}")
                
        except Exception as e:
            print(f"❌ Error al obtener órdenes: {e}")

    async def cancel_order(self):
        """Cancelar una orden."""
        print("\n❌ CANCELAR ORDEN")
        print("-" * 40)
        
        order_id = input("ID de la orden a cancelar: ").strip()
        
        try:
            await self.executor.cancel_order(order_id)
            print(f"✅ Orden {order_id} cancelada exitosamente!")
            
        except Exception as e:
            print(f"❌ Error al cancelar orden: {e}")

    async def view_positions(self):
        """Ver posiciones actuales."""
        print("\n💼 POSICIONES ACTUALES")
        print("-" * 60)
        
        try:
            positions = await self.executor.get_positions()
            
            if not positions:
                print("No hay posiciones abiertas.")
                return
            
            for i, pos in enumerate(positions, 1):
                position_type = "LONG" if pos.quantity > 0 else "SHORT"
                print(f"\n{i}. {pos.symbol} ({position_type})")
                print(f"   Cantidad: {abs(pos.quantity)}")
                print(f"   Costo promedio: ${pos.average_cost}")
                print(f"   Valor de mercado: ${pos.market_value}")
                print(f"   P&L no realizado: ${pos.unrealized_pnl}")
                
        except Exception as e:
            print(f"❌ Error al obtener posiciones: {e}")

    def view_order_history(self):
        """Ver historial de órdenes enviadas en esta sesión."""
        print("\n📝 HISTORIAL DE ÓRDENES (Esta sesión)")
        print("-" * 60)
        
        if not self.submitted_orders:
            print("No se han enviado órdenes en esta sesión.")
            return
        
        for i, order in enumerate(self.submitted_orders, 1):
            print(f"\n{i}. Order ID: {order.order_id}")
            print(f"   Client ID: {order.client_order_id}")
            print(f"   {order.side.value} {order.quantity} {order.symbol}")
            print(f"   Tipo: {order.order_type.value}")
            print(f"   Estado inicial: {order.status.value}")

    async def run(self):
        """Ejecutar el programa interactivo."""
        print("\n🚀 Bienvenido al Probador Interactivo de Órdenes IBKR")
        print("=" * 60)
        
        # Configuración de conexión
        use_defaults = input("\n¿Usar configuración por defecto (127.0.0.1:7497)? (S/n): ").strip().lower()
        
        if use_defaults in ['', 's', 'si', 'yes', 'y']:
            host = "127.0.0.1"
            port = 7497
        else:
            host = input("Host [127.0.0.1]: ").strip() or "127.0.0.1"
            port = int(input("Puerto [7497]: ").strip() or "7497")
        
        # Conectar
        if not await self.connect(host, port):
            return
        
        try:
            # Menú principal
            while True:
                self.print_menu()
                choice = input("\nSelecciona una opción (1-9): ").strip()
                
                if choice == '1':
                    await self.create_market_order()
                elif choice == '2':
                    await self.create_limit_order()
                elif choice == '3':
                    await self.create_stop_order()
                elif choice == '4':
                    await self.create_stop_limit_order()
                elif choice == '5':
                    await self.view_open_orders()
                elif choice == '6':
                    await self.cancel_order()
                elif choice == '7':
                    await self.view_positions()
                elif choice == '8':
                    self.view_order_history()
                elif choice == '9':
                    print("\n👋 ¡Hasta luego!")
                    break
                else:
                    print("❌ Opción inválida. Intenta de nuevo.")
                
                input("\nPresiona Enter para continuar...")
                
        finally:
            await self.disconnect()


async def main():
    """Punto de entrada principal."""
    tester = InteractiveOrderTester()
    await tester.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Programa interrumpido. ¡Hasta luego!")

