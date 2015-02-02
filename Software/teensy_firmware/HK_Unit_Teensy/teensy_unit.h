#ifndef _TEENSY_UNIT_H
#define _TEENSY_UNIT_H


#include "wave_table.h"
#include "i2c_t3.h"
#include "PWMDriver.h"
#include "Arduino.h"

#define packet_size 64
#define i2c_timeout 1000 //microsecond

class TeensyUnit{
	
	public:
	
		//===============================================
		//==== pin assignments ====
		//===============================================
		
		//--- Teensy on-board ---
		const uint8_t indicator_led_pin = 13;
		
		//--- Programming Pin ---
		const uint8_t PGM_DO_pin = 7;
		
		//--- Fast PWM pins ---
		const uint8_t FPWM_1_pin[2] = {3, 4};
		const uint8_t FPWM_2_pin[2] = {6, 5};
		const uint8_t FPWM_3_pin[0] = {};
		const uint8_t FPWM_4_pin[2] = {20, 21};
		const uint8_t FPWM_5_pin[2] = {25, 32};
		const uint8_t FPWM_6_pin[0] = {};
		const uint8_t* FPWM_pin[6];
		
		//--- Analogue pins ---
		const uint8_t Analog_1_pin[2] = {A11, A13};
		const uint8_t Analog_2_pin[2] = {A12, A15};
		const uint8_t Analog_3_pin[2] = {A16, A17};
		const uint8_t Analog_4_pin[2] = {A8, A9};
		const uint8_t Analog_5_pin[2] = {A2, A3};
		const uint8_t Analog_6_pin[2] = {A0, A1};
		const uint8_t* Analog_pin[6];
		
		//--- UART pins ---
		const uint8_t RX1_pin = 0;  //not being used
		const uint8_t TX1_pin = 1;  //not being used
		
		//--- SPI pins ---
		const uint8_t CE = 9;		//not being used
		const uint8_t CSN = 10;		//not being used
		const uint8_t MOSI = 11;	//not being used
		const uint8_t MISO = 12;	//not being used
		const uint8_t SCK = 13;		//not being used
		
		//--- Slow PWM pin ----
		const uint8_t SPWM_1_pin[2] = {0, 1};
		const uint8_t SPWM_2_pin[2] = {2, 3};
		const uint8_t SPWM_3_pin[4] = {4, 5, 6, 7};
		const uint8_t SPWM_4_pin[2] = {14, 15};
		const uint8_t SPWM_5_pin[2] = {12, 13};
		const uint8_t SPWM_6_pin[4] = {8, 9 , 10, 11};
		const uint8_t* SPWM_pin[6];
		
		//--- I2C Multiplexer pins ---
		const uint8_t I2C_MUL_ADR_pin[3] = {2, 24, 33};
		const uint8_t I2C_MUL_ADR[6] = {4, 6, 7, 2, 1, 0};
		


		
		
		//===============================================
		//==== Functions ====
		//===============================================
		
		//--- Constructor and destructor ---
		TeensyUnit();
		~TeensyUnit();

		//--- Initialization ---
		void init();
		
		//--- Communication functions ----
		bool receive_msg();
		void send_msg();
		virtual void parse_msg() = 0;
		virtual void compose_reply(byte front_signature, byte back_signature) = 0;
		
		
	protected:
		
		//==== constants ====
		const uint8_t num_outgoing_byte = packet_size;
		const uint8_t num_incoming_byte = packet_size;
		
		i2c_t3 Wire;
		
		//==== COMMUNICATION variables =====
		byte send_data_buff[packet_size];
		byte recv_data_buff[packet_size];
		uint8_t request_type = 0;
		
		//=== initialize slow pwm ===
		PWMDriver spwm;	
		void spwm_init(uint16_t freq=1000);
		
		//==== Port Classes ====
		
		//--- Tentacle ---
		class TentaclePort{
		
			public:
			
				//~~constructor and destructor~~
				TentaclePort(TeensyUnit& teensy_parent, const uint8_t Port_Id);
				~TentaclePort();
				void init();

				//~~outputs~~
				void set_sma_level(const uint8_t id, const uint8_t level);
				void set_led_level(const uint8_t id, const uint8_t level);
				
				//~~inputs~~
				uint8_t read_analog_state(const uint8_t id);  //{IR 0, IR 1}
				bool read_acc_state(int16_t &accel_x, int16_t &accel_y, int16_t &accel_z);  // return array:{x, y, z}
				
				
				//~~configurations~~
				const uint8_t port_id;
				const bool is_all_slow;
				uint8_t sma_pins[2];
				uint8_t led_pins[2];
				uint8_t analog_pins[2];
				uint8_t acc_pin;
				
			private:
			
				TeensyUnit& teensy_unit;
				
				
				//~~accelerometer configurations~~
					
				const uint8_t ACCEL = 0x53; //Accel I2C Address    

				const uint8_t  ACC_ACT_ADDR = 0x27; //ACC Activity/Inactivity control byte
				const uint8_t  ACC_ACT_VAL = 0x00;

				const uint8_t  ACC_BW_ADDR = 0x2C; //ACC BW control byte
				const uint8_t  ACC_BW_VAL = 0x0D; 

				const uint8_t  ACC_PWRCTRL_ADDR = 0x2D; //ACC Power control byte
				const uint8_t  ACC_PWRCTRL_SLEEP = 0x00; 
				const uint8_t  ACC_PWRCTRL_MEASURE = 0x08; 

				const uint8_t  ACC_INRPPT_ADDR = 0x2E; //ACC Interupt control byte
				const uint8_t  ACC_INRPPT_DISABLE = 0x00;  //disable interupt

				const uint8_t  ACC_DATAFORMAT_ADDR = 0x31; //ACC data format byte
				const uint8_t  ACC_DATAFORMAT_VALUE = 0x00;  //Set the range to +/- 16g and make the value right justified with sign extention

				const uint8_t  ACC_FIFO_ADDR = 0x38; //ACC FIFO byte
				const uint8_t  ACC_FIFO_VALUE = 0x00;  // Bypass FIFO

				const uint8_t  ACC_X_LSB_ADDR = 0x32;// ACC X axis LSB byte
								
				
				void switchToAccel(); // switching to the correct accelerometer
				void writeToAccel(const byte address, const byte val);
				
				
		};
	
	
		//--- Protocell Port ---
		class ProtocellPort{
			
			public:
			
				//~~constructor and destructor~~
				ProtocellPort(TeensyUnit& teensy_parent, const uint8_t Port_Id);
				~ProtocellPort();

				//~~outputs~~
				void set_led_level(const uint8_t level);
				
				//~~inputs~~
				uint8_t read_analog_state(); 
				
				
				//~~configurations~~
				const uint8_t port_id;
				const bool is_slow;
				uint8_t led_pin;
				uint8_t analog_pin;
				
			private:
				TeensyUnit& teensy_unit;
			
		
		};
		
		
		//===============================================
		//==== Ports ====
		//===============================================
		
		TentaclePort tentacle_0;
		TentaclePort tentacle_1;
		TentaclePort tentacle_2;
		TentaclePort tentacle[3];
		TentaclePort extra_lights;
		
};
#endif
