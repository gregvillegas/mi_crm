package com.microimage.crm.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.microimage.crm.api.RetrofitClient
import com.microimage.crm.model.Proposal
import com.microimage.crm.model.SalesActivity
import com.microimage.crm.model.SalesFunnel
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(token: String) {
    val scope = rememberCoroutineScope()
    var funnelEntries by remember { mutableStateOf<List<SalesFunnel>>(emptyList()) }
    var proposals by remember { mutableStateOf<List<Proposal>>(emptyList()) }
    var activities by remember { mutableStateOf<List<SalesActivity>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        scope.launch {
            try {
                val authHeader = "Token $token"
                
                // Fetch all data in parallel
                val funnelResponse = RetrofitClient.apiService.getSalesFunnel(authHeader)
                val proposalsResponse = RetrofitClient.apiService.getProposals(authHeader)
                val activitiesResponse = RetrofitClient.apiService.getSalesActivities(authHeader)

                if (funnelResponse.isSuccessful) funnelEntries = funnelResponse.body() ?: emptyList()
                if (proposalsResponse.isSuccessful) proposals = proposalsResponse.body() ?: emptyList()
                if (activitiesResponse.isSuccessful) activities = activitiesResponse.body() ?: emptyList()

            } catch (e: Exception) {
                errorMessage = "Failed to load data: ${e.message}"
            } finally {
                isLoading = false
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Dashboard") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { paddingValues ->
        Box(modifier = Modifier.padding(paddingValues).fillMaxSize()) {
            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else if (errorMessage != null) {
                Text(
                    text = errorMessage!!,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.align(Alignment.Center).padding(16.dp)
                )
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // --- SALES FUNNEL SECTION ---
                    item {
                        SectionHeader("Sales Funnel", "(${funnelEntries.size} Active)")
                    }
                    if (funnelEntries.isEmpty()) {
                        item { EmptyState("No active deals in funnel") }
                    } else {
                        items(funnelEntries.take(3)) { item ->
                            FunnelCard(item)
                        }
                    }

                    // --- PROPOSALS SECTION ---
                    item {
                        SectionHeader("Recent Proposals", "(${proposals.size})")
                    }
                    if (proposals.isEmpty()) {
                        item { EmptyState("No proposals found") }
                    } else {
                        items(proposals.take(3)) { item ->
                            ProposalCard(item)
                        }
                    }

                    // --- ACTIVITIES SECTION ---
                    item {
                        SectionHeader("Upcoming Activities", "(${activities.size})")
                    }
                    if (activities.isEmpty()) {
                        item { EmptyState("No upcoming activities") }
                    } else {
                        items(activities.take(3)) { item ->
                            ActivityCard(item)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun SectionHeader(title: String, subtitle: String = "") {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )
        if (subtitle.isNotEmpty()) {
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = Color.Gray
            )
        }
    }
}

@Composable
fun EmptyState(message: String) {
    Text(
        text = message,
        style = MaterialTheme.typography.bodyMedium,
        color = Color.Gray,
        modifier = Modifier.padding(start = 8.dp, bottom = 8.dp)
    )
}

@Composable
fun FunnelCard(item: SalesFunnel) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF3E0)) // Light Orange
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = item.companyName, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(4.dp))
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(text = item.stage, style = MaterialTheme.typography.bodyMedium)
                Text(
                    text = "₱${String.format("%,.2f", item.retail)}",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Bold
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
            LinearProgressIndicator(
                progress = item.probability / 100f,
                modifier = Modifier.fillMaxWidth().height(6.dp),
                color = MaterialTheme.colorScheme.primary
            )
            Text(
                text = "${item.probability}% Probability",
                style = MaterialTheme.typography.labelSmall,
                modifier = Modifier.align(Alignment.End)
            )
        }
    }
}

@Composable
fun ProposalCard(item: Proposal) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFE3F2FD)) // Light Blue
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(text = item.proposalNumber, style = MaterialTheme.typography.labelMedium, color = Color.Gray)
                Text(
                    text = item.status,
                    style = MaterialTheme.typography.labelMedium,
                    color = if (item.status == "Accepted") Color(0xFF2E7D32) else Color.Gray,
                    fontWeight = FontWeight.Bold
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = item.subject, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(text = item.customerName, style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "${item.currency} ${String.format("%,.2f", item.totalAmount)}",
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
fun ActivityCard(item: SalesActivity) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF3E5F5)) // Light Purple
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                // Simple icon placeholder
                Box(
                    modifier = Modifier
                        .size(12.dp)
                        .background(Color.Magenta, shape = RoundedCornerShape(50))
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = item.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = "Customer: ${item.customerName ?: "N/A"}", style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(4.dp))
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(text = item.status, style = MaterialTheme.typography.labelMedium)
                Text(
                    text = item.scheduledStart?.take(10) ?: "No Date", // Simple date truncation
                    style = MaterialTheme.typography.labelMedium,
                    color = Color.Gray
                )
            }
        }
    }
}
