package com.microimage.crm.ui.proposal

import android.widget.Toast
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.microimage.crm.api.RetrofitClient
import com.microimage.crm.model.CustomerSummary
import com.microimage.crm.model.ProposalCreatePayload
import com.microimage.crm.model.ProposalItemPayload
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProposalCreateScreen(token: String, navController: NavController) {
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    
    var customers by remember { mutableStateOf<List<CustomerSummary>>(emptyList()) }
    var selectedCustomer by remember { mutableStateOf<CustomerSummary?>(null) }
    var expanded by remember { mutableStateOf(false) }
    
    var subject by remember { mutableStateOf("") }
    var items by remember { mutableStateOf(listOf(ProposalItemPayload(description = "", quantity = 1.0, unitPrice = 0.0))) }
    
    var isSubmitting by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        val res = RetrofitClient.apiService.getCustomers("Token $token")
        if (res.isSuccessful) customers = res.body() ?: emptyList()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Create Proposal") },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
                .fillMaxSize()
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Customer Dropdown
            ExposedDropdownMenuBox(
                expanded = expanded,
                onExpandedChange = { expanded = !expanded }
            ) {
                OutlinedTextField(
                    value = selectedCustomer?.companyName ?: "Select Customer",
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Customer") },
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                    modifier = Modifier.fillMaxWidth().menuAnchor()
                )
                ExposedDropdownMenu(
                    expanded = expanded,
                    onDismissRequest = { expanded = false }
                ) {
                    customers.forEach { customer ->
                        DropdownMenuItem(
                            text = { Text(customer.companyName) },
                            onClick = {
                                selectedCustomer = customer
                                expanded = false
                            }
                        )
                    }
                }
            }

            OutlinedTextField(
                value = subject,
                onValueChange = { subject = it },
                label = { Text("Subject") },
                modifier = Modifier.fillMaxWidth()
            )

            Text("Line Items", style = MaterialTheme.typography.titleLarge)
            
            items.forEachIndexed { index, item ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(8.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Item ${index + 1}", modifier = Modifier.weight(1f))
                            IconButton(onClick = {
                                if (items.size > 1) {
                                    items = items.toMutableList().apply { removeAt(index) }
                                }
                            }) {
                                Icon(Icons.Default.Delete, contentDescription = "Remove", tint = MaterialTheme.colorScheme.error)
                            }
                        }
                        OutlinedTextField(
                            value = item.description,
                            onValueChange = { desc ->
                                items = items.toMutableList().apply {
                                    this[index] = this[index].copy(description = desc)
                                }
                            },
                            label = { Text("Description") },
                            modifier = Modifier.fillMaxWidth()
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedTextField(
                                value = item.quantity.toString(),
                                onValueChange = { q ->
                                    items = items.toMutableList().apply {
                                        this[index] = this[index].copy(quantity = q.toDoubleOrNull() ?: 0.0)
                                    }
                                },
                                label = { Text("Qty") },
                                modifier = Modifier.weight(1f),
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                            )
                            OutlinedTextField(
                                value = item.unitPrice.toString(),
                                onValueChange = { p ->
                                    items = items.toMutableList().apply {
                                        this[index] = this[index].copy(unitPrice = p.toDoubleOrNull() ?: 0.0)
                                    }
                                },
                                label = { Text("Price") },
                                modifier = Modifier.weight(1f),
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                            )
                        }
                    }
                }
            }

            Button(
                onClick = {
                    items = items + ProposalItemPayload(description = "", quantity = 1.0, unitPrice = 0.0)
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(Icons.Default.Add, contentDescription = null)
                Text("Add Item")
            }

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = {
                    if (selectedCustomer == null || subject.isBlank()) {
                        Toast.makeText(context, "Customer and Subject required", Toast.LENGTH_SHORT).show()
                        return@Button
                    }
                    isSubmitting = true
                    scope.launch {
                        try {
                            val payload = ProposalCreatePayload(
                                customer = selectedCustomer!!.id,
                                subject = subject,
                                items = items
                            )
                            val res = RetrofitClient.apiService.createProposal("Token $token", payload)
                            if (res.isSuccessful) {
                                Toast.makeText(context, "Proposal Created", Toast.LENGTH_SHORT).show()
                                navController.popBackStack()
                            }
                        } catch (e: Exception) {
                            Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
                        } finally {
                            isSubmitting = false
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth().height(56.dp),
                enabled = !isSubmitting
            ) {
                if (isSubmitting) CircularProgressIndicator(color = Color.White)
                else Text("Create Proposal")
            }
        }
    }
}
