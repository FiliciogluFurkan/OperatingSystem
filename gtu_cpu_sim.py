import sys
import argparse

# --- Constants for Opcodes ---
OP_SET = "SET"
OP_CPY = "CPY"
OP_CPYI = "CPYI"
OP_ADD = "ADD"
OP_ADDI = "ADDI"
OP_SUBI = "SUBI"
OP_JIF = "JIF"
OP_PUSH = "PUSH"
OP_POP = "POP"
OP_CALL = "CALL"
OP_RET = "RET"
OP_HLT = "HLT"
OP_USER = "USER"
OP_SYSCALL = "SYSCALL"
OP_CPYI2 = "CPYI2"

# SYSCALL sub-types
SYSCALL_PRN = "PRN"
SYSCALL_HLT_THREAD = "HLT_THREAD"
SYSCALL_YIELD = "YIELD"

# Memory Mapped Registers
MEM_PC = 0
MEM_SP = 1
MEM_SYSCALL_RESULT = 2
MEM_INSTR_COUNT = 3
MEM_RESERVED_START = 4
MEM_RESERVED_END = 20

# CPU Modes
MODE_KERNEL = 0
MODE_USER = 1

# Memory size
MEMORY_SIZE = 16384

# Syscall IDs
SYSCALL_ID_PRN = 1
SYSCALL_ID_HLT_THREAD = 2
SYSCALL_ID_YIELD = 3
SYSCALL_ID_UNKNOWN = 0

# Special memory addresses
MEM_ADDR_SYSCALL_ID = 4
MEM_ADDR_SYSCALL_ARG1 = 5

# --- CPU Class ---
class CPU:
    def __init__(self, memory_size=MEMORY_SIZE):
        self.memory = [0] * memory_size
        self.halted = False
        self.mode = MODE_KERNEL

        # Initialize special registers
        self.memory[MEM_PC] = 0
        self.memory[MEM_SP] = memory_size - 1
        self.memory[MEM_INSTR_COUNT] = 0
        
        # For instruction mapping
        self.instruction_map = {}
        self.current_thread_id = 1
        self.threads_blocked_until = {}
        
        # Thread table management - 10 threads support
        self.max_threads = 10
        self.thread_table_base = 21  # Memory address 21-120 for thread table
        
        # Thread tracking için yeni özellikler
        self.thread_instruction_counts = {i: 0 for i in range(1, 11)}  # Her thread'in instruction sayısı
        self.thread_start_times = {i: -1 for i in range(1, 11)}        # Thread başlama zamanları
        self.thread_states = {i: "INACTIVE" for i in range(1, 11)}     # Thread durumları
        
        # İlk 4 thread'i aktif olarak işaretle
        for i in range(1, 5):
            self.thread_states[i] = "READY"
            self.thread_start_times[i] = 0

    @property
    def PC(self):
        return self.memory[MEM_PC]

    @PC.setter
    def PC(self, value):
        self.memory[MEM_PC] = value

    @property
    def SP(self):
        return self.memory[MEM_SP]

    @SP.setter
    def SP(self, value):
        self.memory[MEM_SP] = value

    @property
    def instr_executed_count(self):
        return self.memory[MEM_INSTR_COUNT]

    @instr_executed_count.setter
    def instr_executed_count(self, value):
        self.memory[MEM_INSTR_COUNT] = value

    def get_thread_state(self, tid):
        """Thread'in gerçek durumunu belirle"""
        # Terminated thread'ler
        if tid in self.threads_blocked_until and self.threads_blocked_until[tid] == -1:
            return "TERM"
        
        # Blocked thread'ler
        if tid in self.threads_blocked_until and self.threads_blocked_until[tid] > self.instr_executed_count:
            return "BLCK"
        
        # Running thread
        if tid == self.current_thread_id and self.mode == MODE_USER:
            return "RUN"
        
        # Ready threads (1-4 arası aktif thread'ler)
        if 1 <= tid <= 4:
            pc_save_addr = 180 + (tid - 1)
            if pc_save_addr < len(self.memory) and self.memory[pc_save_addr] > 0:  # PC > 0 ise aktif
                return "RDY"
        
        # Inactive threads (5-10)
        return "INACT"

    def print_thread_table(self, debug_level):
        """Geliştirilmiş Debug Mode 3: Thread table gösterimi"""
        if debug_level >= 3:
            print("\n=== THREAD TABLE DEBUG (Mode 3) ===")
            print("TID | State | PC   | SP   | StartTime | InstrCount")
            print("----|-------|------|------|-----------|----------")

            for tid in range(1, 11):
                # Thread table base address
                thread_table_base = 21 + (tid - 1) * 20

                # PC ve SP değerlerini oku
                if thread_table_base + 3 < len(self.memory):
                    pc_val = self.memory[thread_table_base + 2]
                    sp_val = self.memory[thread_table_base + 3]
                else:
                    pc_val = 0
                    sp_val = 16000 - tid * 1000

                # Değerlerin integer olduğundan emin ol
                try:
                    pc_val = int(pc_val) if pc_val is not None else 0
                    sp_val = int(sp_val) if sp_val is not None else (16000 - tid * 1000)
                except (ValueError, TypeError):
                    pc_val = 0
                    sp_val = 16000 - tid * 1000

                # Thread state'ini belirle
                state = self.get_thread_state(tid)
                
                # Start time ve instruction count
                start_time = self.thread_start_times.get(tid, -1)
                instr_count = self.thread_instruction_counts.get(tid, 0)
                
                # Start time -1 ise (hiç başlamamış), "N/A" göster
                start_str = "N/A" if start_time == -1 else f"{start_time}"
                
                print(f" {tid:2d} | {state:5s} | {pc_val:4d} | {sp_val:4d} | {start_str:>9s} | {instr_count:10d}")

            print("=" * 55)
            print()

    def update_thread_table(self, thread_id, state=None, pc=None, sp=None):
        """Update thread table in memory"""
        thread_table_base = 21 + (thread_id - 1) * 20

        if thread_table_base + 3 < len(self.memory):
            # Update thread ID
            self._write_mem(thread_table_base, thread_id)

            # Update state if provided
            if state is not None:
                self._write_mem(thread_table_base + 1, state)

            # Update PC if provided
            if pc is not None:
                self._write_mem(thread_table_base + 2, pc)

            # Update SP if provided
            if sp is not None:
                self._write_mem(thread_table_base + 3, sp)
        
    def _check_user_mode_access(self, address):
        if self.mode == MODE_USER and address < 1000:
            print(f"USER MODE VIOLATION: Attempt to access memory address {address}. Thread terminated.")
            self.halted = True
            return False
        return True

    def _read_mem(self, address):
        if not self._check_user_mode_access(address):
            return None
        if 0 <= address < len(self.memory):
            return self.memory[address]
        else:
            print(f"Error: Memory read out of bounds at address {address}")
            self.halted = True
            return None

    def _write_mem(self, address, value):
        if not self._check_user_mode_access(address):
            return False
        if 0 <= address < len(self.memory):
            self.memory[address] = value
            return True
        else:
            print(f"Error: Memory write out of bounds at address {address}")
            self.halted = True
            return False

    def load_program_from_parsed(self, initial_data, instructions_parsed, instruction_start_addr=200):
        print("Loading program...")
        
        # Load initial data
        for addr, val in initial_data.items():
            if not self._write_mem(addr, val): 
                return False
            if addr < 20 or addr >= 1000:  # Only show interesting addresses
                print(f"  Data: mem[{addr}] = {val}")
    
        # Load instructions
        current_mem_addr = instruction_start_addr
        self.instruction_map = {}
    
        for i, instr_parts in enumerate(instructions_parsed):
            self.instruction_map[i] = current_mem_addr
            op_str = instr_parts[0]
            args = instr_parts[1:]
    
            if not self._write_mem(current_mem_addr, op_str): 
                return False
            current_mem_addr += 1
            
            for arg in args:
                if not self._write_mem(current_mem_addr, arg): 
                    return False
                current_mem_addr += 1
        
        # Set initial PC
        if MEM_PC not in initial_data:
             self.PC = instruction_start_addr
        else:
             self.PC = self.memory[MEM_PC]
    
        print(f"Program loaded. Initial PC = {self.PC}")
        print(f"Instructions mapped: {len(self.instruction_map)}")
        return True

    def handle_syscall_blocking(self, syscall_id, arg_addr, debug_level=0):
        """Handle syscalls with blocking behavior"""
        
        if syscall_id == SYSCALL_ID_PRN:
            # PRN: Print and block thread
            val_to_print = self._read_mem(arg_addr)
            if val_to_print is not None:
                print(f"THREAD_{self.current_thread_id}_OUTPUT: {val_to_print}")
                
                # Block thread for 100 cycles
                unblock_cycle = self.instr_executed_count + 100
                self.threads_blocked_until[self.current_thread_id] = unblock_cycle
                
                # Update thread table state to BLOCKED (3) for display
                thread_table_base = 21 + (self.current_thread_id - 1) * 20
                if thread_table_base + 1 < len(self.memory):
                    self._write_mem(thread_table_base + 1, 3)  # State = BLOCKED
                
                if debug_level > 0:
                    print(f"  SYSCALL: Thread {self.current_thread_id} blocked until cycle {unblock_cycle}")
                
                return True
        
        elif syscall_id == SYSCALL_ID_HLT_THREAD:
            # HLT_THREAD: Terminate thread
            if debug_level > 0:
                print(f"  SYSCALL: Thread {self.current_thread_id} terminated")
            
            # Update thread table state to TERMINATED (0) for display
            thread_table_base = 21 + (self.current_thread_id - 1) * 20
            if thread_table_base + 1 < len(self.memory):
                self._write_mem(thread_table_base + 1, 0)  # State = TERMINATED
            
            # Mark as terminated in tracking
            self.threads_blocked_until[self.current_thread_id] = -1
            
            # Mark PC as 0 in the PC save area to prevent re-execution
            pc_save_addr = 180 + (self.current_thread_id - 1)  # 180, 181, 182, 183
            if not self._write_mem(pc_save_addr, 0):
                return False
            
            if debug_level > 0:
                print(f"  Thread {self.current_thread_id} PC save area ({pc_save_addr}) set to 0")
            
            # Check if all active threads are terminated
            active_threads = [tid for tid in range(1, 5)  # Only check threads 1-4
                            if tid not in self.threads_blocked_until or 
                               self.threads_blocked_until[tid] != -1]
            
            if len(active_threads) <= 1:  # Only current thread left
                if debug_level > 0:
                    print("  All active threads terminated, halting CPU")
                self.halted = True
            
            return True
        
        elif syscall_id == SYSCALL_ID_YIELD:
            # YIELD: Just continue to scheduler
            if debug_level > 0:
                print(f"  SYSCALL: Thread {self.current_thread_id} yielded")
            return True
        
        return True

    def step(self, debug_level=0):
        if self.halted:
            return False

        # USER mode'da ise, current thread'in instruction count'unu artır
        if self.mode == MODE_USER:
            self.thread_instruction_counts[self.current_thread_id] += 1
            
            # Thread ilk kez çalışıyorsa start time'ı kaydet
            if self.thread_start_times[self.current_thread_id] == -1:
                self.thread_start_times[self.current_thread_id] = self.instr_executed_count

        # Check if any blocked threads should be unblocked
        current_cycle = self.instr_executed_count
        for tid, unblock_cycle in list(self.threads_blocked_until.items()):
            if unblock_cycle != -1 and current_cycle >= unblock_cycle:
                del self.threads_blocked_until[tid]
                
                # Update thread table state to READY
                thread_table_base = 21 + (tid - 1) * 20
                if thread_table_base + 1 < len(self.memory):
                    self._write_mem(thread_table_base + 1, 1)  # State = READY
                
                if debug_level > 0:
                    print(f"  Thread {tid} unblocked at cycle {current_cycle}")

        current_pc = self.PC
        if current_pc is None or not (0 <= current_pc < len(self.memory)):
            print(f"Error: PC ({current_pc}) is out of bounds.")
            self.halted = True
            return False

        opcode_val = self._read_mem(current_pc)
        if opcode_val is None:
            return False

        opcode = str(opcode_val)
        pc_incremented = False

        if debug_level > 0:
            mode_str = 'USER' if self.mode == MODE_USER else 'KERNEL'
            print(f"Cycle {self.instr_executed_count}: PC={current_pc}, Opcode='{opcode}', Mode={mode_str}")

        if opcode == OP_SET:
            val_b = self._read_mem(current_pc + 1)
            addr_a = self._read_mem(current_pc + 2)
            if val_b is None or addr_a is None: 
                return False

            if addr_a == MEM_PC:
                # Jump to instruction number
                target_instr_num = val_b
                if target_instr_num in self.instruction_map:
                    self.PC = self.instruction_map[target_instr_num]
                    if debug_level > 0: 
                        print(f"  SET: PC = instr_map[{target_instr_num}] -> {self.PC}")
                else:
                    print(f"  SET Error: Invalid instruction number {target_instr_num}")
                    self.halted = True
                    return False
                pc_incremented = True
            else:
                if not self._write_mem(addr_a, val_b): 
                    return False
                if debug_level > 0: 
                    print(f"  SET: mem[{addr_a}] = {val_b}")
            
            if not pc_incremented: 
                self.PC = current_pc + 3

        elif opcode == OP_CPY:
            addr_a1 = self._read_mem(current_pc + 1)
            addr_a2 = self._read_mem(current_pc + 2)
            if addr_a1 is None or addr_a2 is None: 
                return False

            value_from_a1 = self._read_mem(addr_a1)
            if value_from_a1 is None: 
                return False

            if not self._write_mem(addr_a2, value_from_a1): 
                return False
            
            if debug_level > 0: 
                print(f"  CPY: Copied mem[{addr_a1}] ({value_from_a1}) to mem[{addr_a2}]")
            self.PC = current_pc + 3

        elif opcode == OP_CPYI:
            # CPYI A1 A2: Copy content of address pointed by A1 to address A2
            addr_a1 = self._read_mem(current_pc + 1)
            addr_a2 = self._read_mem(current_pc + 2)
            if addr_a1 is None or addr_a2 is None:
                return False

            # Read the address that A1 points to
            indirect_addr = self._read_mem(addr_a1)
            if indirect_addr is None:
                return False

            # Read the value from that indirect address
            value_from_indirect = self._read_mem(indirect_addr)
            if value_from_indirect is None:
                return False

            # Write to A2
            if not self._write_mem(addr_a2, value_from_indirect):
                return False

            if debug_level > 0:
                print(f"  CPYI: mem[{addr_a1}] points to {indirect_addr}, copied mem[{indirect_addr}] ({value_from_indirect}) to mem[{addr_a2}]")
            self.PC = current_pc + 3

        elif opcode == OP_CPYI2:
            # CPYI2 A1 A2: Copy content of address pointed by A1 to address pointed by A2
            addr_a1 = self._read_mem(current_pc + 1)
            addr_a2 = self._read_mem(current_pc + 2)
            if addr_a1 is None or addr_a2 is None:
                return False

            # Read the address that A1 points to
            indirect_addr1 = self._read_mem(addr_a1)
            if indirect_addr1 is None:
                return False

            # Read the address that A2 points to
            indirect_addr2 = self._read_mem(addr_a2)
            if indirect_addr2 is None:
                return False

            # Read the value from the first indirect address
            value_from_indirect = self._read_mem(indirect_addr1)
            if value_from_indirect is None:
                return False

            # Write to the second indirect address
            if not self._write_mem(indirect_addr2, value_from_indirect):
                return False

            if debug_level > 0:
                print(f"  CPYI2: mem[{addr_a1}] points to {indirect_addr1}, mem[{addr_a2}] points to {indirect_addr2}, copied mem[{indirect_addr1}] ({value_from_indirect}) to mem[{indirect_addr2}]")
            self.PC = current_pc + 3

        elif opcode == OP_ADD:
            addr_a = self._read_mem(current_pc + 1)
            val_b = self._read_mem(current_pc + 2)
            if addr_a is None or val_b is None: 
                return False

            current_val_a = self._read_mem(addr_a)
            if current_val_a is None: 
                return False
            
            if not self._write_mem(addr_a, current_val_a + val_b): 
                return False
            if debug_level > 0: 
                print(f"  ADD: mem[{addr_a}] = {current_val_a} + {val_b} -> {self.memory[addr_a]}")
            self.PC = current_pc + 3

        elif opcode == OP_SUBI:
            addr_a1 = self._read_mem(current_pc + 1)
            addr_a2 = self._read_mem(current_pc + 2)
            if addr_a1 is None or addr_a2 is None: 
                return False

            val_from_a1 = self._read_mem(addr_a1)
            val_from_a2 = self._read_mem(addr_a2)
            if val_from_a1 is None or val_from_a2 is None: 
                return False
            
            result = val_from_a1 - val_from_a2
            
            if not self._write_mem(addr_a2, result): 
                return False
            
            if debug_level > 0: 
                print(f"  SUBI: mem[{addr_a1}] ({val_from_a1}) - mem[{addr_a2}] ({val_from_a2}) = {result}. Stored in mem[{addr_a2}]")
            self.PC = current_pc + 3

        elif opcode == OP_JIF:
            addr_a = self._read_mem(current_pc + 1)
            target_instr_num = self._read_mem(current_pc + 2)
            if addr_a is None or target_instr_num is None: 
                return False
            
            val_a = self._read_mem(addr_a)
            if val_a is None: 
                return False

            if val_a <= 0:
                if target_instr_num in self.instruction_map:
                    self.PC = self.instruction_map[target_instr_num]
                    if debug_level > 0: 
                        print(f"  JIF: mem[{addr_a}] ({val_a}) <= 0. PC = {self.PC}")
                else:
                    print(f"  JIF Error: Invalid instruction number {target_instr_num}")
                    self.halted = True
                    return False
            else:
                self.PC = current_pc + 3
                if debug_level > 0: 
                    print(f"  JIF: mem[{addr_a}] ({val_a}) > 0. No jump.")
            pc_incremented = True

        elif opcode == OP_PUSH:
            addr_a = self._read_mem(current_pc + 1)
            if addr_a is None:
                return False

            value_to_push = self._read_mem(addr_a)
            if value_to_push is None:
                return False

            # Push onto stack (decrement SP first, then store)
            new_sp = self.SP - 1
            if not self._write_mem(new_sp, value_to_push):
                return False
            self.SP = new_sp

            if debug_level > 0:
                print(f"  PUSH: Pushed mem[{addr_a}] ({value_to_push}) onto stack. SP = {self.SP}")
            self.PC = current_pc + 2

        elif opcode == OP_POP:
            addr_a = self._read_mem(current_pc + 1)
            if addr_a is None:
                return False

            # Pop from stack (load from SP, then increment SP)
            value_from_stack = self._read_mem(self.SP)
            if value_from_stack is None:
                return False

            if not self._write_mem(addr_a, value_from_stack):
                return False
            self.SP = self.SP + 1

            if debug_level > 0:
                print(f"  POP: Popped {value_from_stack} from stack to mem[{addr_a}]. SP = {self.SP}")
            self.PC = current_pc + 2

        elif opcode == OP_CALL:
            target_instr_num = self._read_mem(current_pc + 1)
            if target_instr_num is None:
                return False

            # Push return address (next instruction after CALL)
            return_pc = current_pc + 2
            new_sp = self.SP - 1
            if not self._write_mem(new_sp, return_pc):
                return False
            self.SP = new_sp

            # Jump to target instruction
            if target_instr_num in self.instruction_map:
                self.PC = self.instruction_map[target_instr_num]
                if debug_level > 0:
                    print(f"  CALL: Called instruction {target_instr_num}, return address {return_pc} pushed. PC = {self.PC}")
            else:
                print(f"  CALL Error: Invalid instruction number {target_instr_num}")
                self.halted = True
                return False
            pc_incremented = True

        elif opcode == OP_RET:
            # Pop return address from stack
            return_pc = self._read_mem(self.SP)
            if return_pc is None:
                return False
            self.SP = self.SP + 1

            # Jump back to return address
            self.PC = return_pc
            if debug_level > 0:
                print(f"  RET: Returned to PC = {return_pc}, SP = {self.SP}")
            pc_incremented = True

        elif opcode == OP_USER:
            if self.mode != MODE_KERNEL:
                print(f"  USER Error: USER instruction can only be executed in KERNEL mode")
                self.halted = True
                return False
        
            addr_a = self._read_mem(current_pc + 1)
            if addr_a is None: 
                return False
        
            target_pc = self._read_mem(addr_a)
            if target_pc is None:
                return False
            
            # Update current thread ID
            self.current_thread_id = self._read_mem(160)
            
            # Thread ilk kez başlıyorsa start time'ı kaydet
            if self.thread_start_times[self.current_thread_id] == -1:
                self.thread_start_times[self.current_thread_id] = self.instr_executed_count
            
            # Update thread table with RUNNING state and current PC
            self.update_thread_table(self.current_thread_id, state=2, pc=target_pc, sp=self.SP)
            
            self.mode = MODE_USER
            self.PC = target_pc
            
            # Print thread table for debug mode 3
            self.print_thread_table(debug_level)
            
            if debug_level > 0: 
                print(f"  USER: Switched to USER mode. PC = {target_pc}, Thread = {self.current_thread_id}")
            pc_incremented = True

        elif opcode == OP_SYSCALL:
            # 1. SYSCALL parametrelerini oku
            syscall_type_str = self._read_mem(current_pc + 1)  # PRN, HLT_THREAD, YIELD
            syscall_arg_addr = self._read_mem(current_pc + 2)   # Argument address
            
            # Hata kontrolü
            if syscall_type_str is None or syscall_arg_addr is None:
                self.halted = True
                return False
        
            syscall_type_str = str(syscall_type_str).upper()
        
            # 2. Debug mode 3: Thread table'ı göster
            self.print_thread_table(debug_level)
        
            # 3. USER mode'dan KERNEL mode'a geç
            if self.mode == MODE_USER:
                if debug_level > 0: 
                    print(f"  SYSCALL: Switching from USER to KERNEL mode")
                self.mode = MODE_KERNEL
            
            # 4. SYSCALL tipini belirle
            if syscall_type_str == "PRN":
                syscall_id = SYSCALL_ID_PRN
            elif syscall_type_str == "HLT_THREAD":
                syscall_id = SYSCALL_ID_HLT_THREAD
            elif syscall_type_str == "YIELD":
                syscall_id = SYSCALL_ID_YIELD
            else:
                syscall_id = SYSCALL_ID_UNKNOWN
        
            # 5. SYSCALL bilgilerini memory'e yaz
            if not self._write_mem(MEM_ADDR_SYSCALL_ID, syscall_id): 
                return False
            if not self._write_mem(MEM_ADDR_SYSCALL_ARG1, syscall_arg_addr): 
                return False
            
            # 6. SYSCALL tipine göre işlem yap
            if syscall_id == SYSCALL_ID_HLT_THREAD:
                # HLT_THREAD: Thread'i sonlandır
                if debug_level > 0:
                    print(f"  SYSCALL: HLT_THREAD - Terminating thread {self.current_thread_id}")
                
                # Thread table'da TERMINATED olarak işaretle
                self.update_thread_table(self.current_thread_id, state=0, pc=0)
                
                # Thread'i sonlandır (blocking handle)
                self.handle_syscall_blocking(syscall_id, syscall_arg_addr, debug_level)
                
                # Doğrudan scheduler'a git (instruction 31 = memory address'te scheduler)
                if 31 in self.instruction_map:
                    self.PC = self.instruction_map[31]
                    if debug_level > 0:
                        print(f"  SYSCALL: Jumping directly to scheduler at instruction 31")
                else:
                    print("SYSCALL Error: Scheduler not found at instruction 31")
                    self.halted = True
                    return False
                pc_incremented = True
                
            elif syscall_id == SYSCALL_ID_PRN:
                # PRN: Print ve thread'i 100 cycle block et
                if debug_level > 0:
                    print(f"  SYSCALL: PRN - Print and block thread {self.current_thread_id}")
                
                # Thread table'da BLOCKED olarak işaretle
                self.update_thread_table(self.current_thread_id, state=3)
                
                # Print işlemini yap ve thread'i block et
                self.handle_syscall_blocking(syscall_id, syscall_arg_addr, debug_level)
                
                # Return PC'yi kaydet ve OS handler'a git
                return_pc = current_pc + 3
                if not self._write_mem(MEM_SYSCALL_RESULT, return_pc):
                    self.halted = True
                    return False
                
                # OS syscall handler'a git (instruction 4)
                if 4 in self.instruction_map:
                    self.PC = self.instruction_map[4]
                    if debug_level > 0:
                        print(f"  SYSCALL: Jumping to OS handler at instruction 4")
                else:
                    print("SYSCALL Error: OS handler not found at instruction 4")
                    self.halted = True
                    return False
                pc_incremented = True
                
            elif syscall_id == SYSCALL_ID_YIELD:
                # YIELD: CPU'yu bırak, scheduler'a git
                if debug_level > 0:
                    print(f"  SYSCALL: YIELD - Thread {self.current_thread_id} yielding CPU")
                
                # Thread table'da READY olarak işaretle
                self.update_thread_table(self.current_thread_id, state=1)
                
                # Yield işlemini handle et (sadece scheduler'a gitmek için)
                self.handle_syscall_blocking(syscall_id, syscall_arg_addr, debug_level)
                
                # Return PC'yi kaydet ve OS handler'a git
                return_pc = current_pc + 3
                if not self._write_mem(MEM_SYSCALL_RESULT, return_pc):
                    self.halted = True
                    return False
                
                # OS syscall handler'a git (instruction 4)
                if 4 in self.instruction_map:
                    self.PC = self.instruction_map[4]
                    if debug_level > 0:
                        print(f"  SYSCALL: Jumping to OS handler at instruction 4")
                else:
                    print("SYSCALL Error: OS handler not found at instruction 4")
                    self.halted = True
                    return False
                pc_incremented = True
                
            else:
                # Bilinmeyen SYSCALL
                if debug_level > 0:
                    print(f"  SYSCALL: Unknown syscall type '{syscall_type_str}'")
                self.halted = True
                return False
        
        elif opcode == OP_HLT:
            if debug_level > 0: 
                print("  HLT: CPU Halting")
            self.halted = True

        elif opcode == OP_ADDI:
            addr_a1 = self._read_mem(current_pc + 1)
            addr_a2 = self._read_mem(current_pc + 2)
            if addr_a1 is None or addr_a2 is None: 
                return False

            val_from_a1 = self._read_mem(addr_a1)
            val_from_a2 = self._read_mem(addr_a2)
            if val_from_a1 is None or val_from_a2 is None: 
                return False
            
            result = val_from_a1 + val_from_a2
            
            if not self._write_mem(addr_a1, result): 
                return False
            
            if debug_level > 0: 
                print(f"  ADDI: mem[{addr_a1}] ({val_from_a1}) + mem[{addr_a2}] ({val_from_a2}) = {result}. Stored in mem[{addr_a1}]")
            self.PC = current_pc + 3    

        else:
            print(f"Error: Unknown opcode '{opcode}' at PC={current_pc}")
            self.halted = True
            return False

        if not pc_incremented and not self.halted:
            pass  # PC was already advanced

        self.instr_executed_count += 1
        return True

    def run(self, max_cycles=5000, debug_level=0):
        print("\n--- CPU RUNNING ---")
        self.halted = False
        
        cycles = 0
        while not self.halted and cycles < max_cycles:
            if not self.step(debug_level=debug_level):
                break
            cycles += 1
            
            if debug_level == 2:
                print("--- Press Enter to continue ---")
                input()
        
        print("--- CPU HALTED or Max Cycles Reached ---")
        print(f"Total cycles executed: {self.instr_executed_count}")
        
        if cycles >= max_cycles:
            print("Warning: Max cycles reached")
        
        # Show final results
        self.show_results()

    def show_results(self):
        """Geliştirilmiş sonuç gösterimi"""
        print("\n🎉 === SIMULATION RESULTS === 🎉")
        print("Thread Execution Summary:")
        print("TID | Status    | Instructions | Start Time | Result Location | Final Value")
        print("----|-----------|--------------|------------|-----------------|------------")
        
        for tid in range(1, 11):
            status = self.get_thread_state(tid)
            instr_count = self.thread_instruction_counts[tid]
            start_time = self.thread_start_times[tid]
            
            # Thread'in sonuç lokasyonu
            result_addr = tid * 1000 + 80
            final_value = self.memory[result_addr] if result_addr < len(self.memory) else 0
            
            start_str = "N/A" if start_time == -1 else str(start_time)
            
            print(f" {tid:2d} | {status:9s} | {instr_count:12d} | {start_str:10s} | {result_addr:15d} | {final_value:11d}")

        print("\nDetailed Thread Results:")
        for tid in range(1, 5):  # Sadece aktif thread'ler
            thread_data_base = tid * 1000 + 80
            if thread_data_base < len(self.memory):
                result = self.memory[thread_data_base]
                instr_count = self.thread_instruction_counts[tid]
                print(f"Thread {tid}: Executed {instr_count} instructions, Result = {result}")

        print(f"\nTotal CPU cycles: {self.instr_executed_count}")
        print(f"Active threads: {sum(1 for tid in range(1, 5) if self.thread_instruction_counts[tid] > 0)}")

    def dump_memory_relevant(self, start_addr, end_addr):
        print(f"Memory dump [{start_addr}-{end_addr-1}]:")
        for i in range(start_addr, end_addr):
            if i < len(self.memory) and self.memory[i] != 0:
                print(f"  mem[{i:03d}] = {self.memory[i]}")

    def show_instruction_map(self):
        print("\n=== INSTRUCTION MAP ===")
        for instr_num, mem_addr in sorted(self.instruction_map.items()):
            opcode = self.memory[mem_addr]
            print(f"Instruction {instr_num}: mem[{mem_addr}] = {opcode}")

# --- Parser ---
def parse_gtu_code(code_string):
    initial_data = {}
    instructions = []
    
    in_data_section = False
    in_instruction_section = False

    lines = code_string.strip().split('\n')

    for line_num, raw_line in enumerate(lines):
        line = raw_line.split('#')[0].strip()
        if not line:
            continue

        if line == "Begin Data Section":
            in_data_section = True
            continue
        elif line == "End Data Section":
            in_data_section = False
            continue
        elif line == "Begin Instruction Section":
            in_instruction_section = True
            continue
        elif line == "End Instruction Section":
            in_instruction_section = False
            continue

        parts = line.split()
        if not parts:
            continue

        if in_data_section:
            try:
                addr = int(parts[0])
                try:
                    val = int(parts[1])
                except ValueError:
                    val = parts[1]
                initial_data[addr] = val
            except (IndexError, ValueError) as e:
                print(f"Error parsing data line: '{raw_line}' -> {e}")
        
        elif in_instruction_section:
            if len(parts) < 2:
                continue

            op_str = parts[1].upper()
            parsed_args = []

            # Parse arguments based on instruction type
            if op_str in [OP_SET, OP_CPY, OP_CPYI, OP_CPYI2, OP_ADD, OP_SUBI, OP_JIF, OP_ADDI]:
                if len(parts) >= 4:
                    parsed_args.append(int(parts[2]))
                    parsed_args.append(int(parts[3]))
            elif op_str in [OP_USER, OP_PUSH, OP_POP, OP_CALL]:
                if len(parts) >= 3:
                    parsed_args.append(int(parts[2]))
            elif op_str == OP_SYSCALL:
                if len(parts) >= 4:
                    parsed_args.append(parts[2].upper())
                    parsed_args.append(int(parts[3]))
            elif op_str in [OP_HLT, OP_RET]:
                pass  # No arguments

            instructions.append([op_str] + parsed_args)
            
    return initial_data, instructions


def load_program_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='GTU-C312 CPU Simulator')
    parser.add_argument('filename', nargs='?', default='os_program.txt', 
                       help='Program file to execute (default: os_program.txt)')
    parser.add_argument('-D', '--debug', type=int, choices=[0,1,2,3], 
                       default=0, help='Debug level (0-3)')
    
    args = parser.parse_args()
    
    cpu = CPU(memory_size=MEMORY_SIZE)

    print("=== GTU-C312 CPU Simulator ===")
    print(f"Loading program from: {args.filename}")
    print(f"Debug level: {args.debug}")
    print("=====================================")

    program_code = load_program_file(args.filename)
    if program_code is None:
        sys.exit(1)

    print("Parsing OS with threads...")
    initial_data, instructions = parse_gtu_code(program_code)

    if cpu.load_program_from_parsed(initial_data, instructions, instruction_start_addr=200):
        cpu.show_instruction_map()  
        cpu.run(max_cycles=5000, debug_level=args.debug)  # 2000 → 5000
    else:
        print("Failed to load program.")
        sys.exit(1)


if __name__ == "__main__":
    main()